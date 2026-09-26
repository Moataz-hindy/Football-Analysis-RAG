"""Retrieve attributable internet excerpts for the advisor's evidence registry.

Search-provider summaries are deliberately excluded. Publication metadata is
recorded as supplied by the provider/page; it is not independently verified.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

from src.agent.types import RetrievedSource


REQUEST_TIMEOUT = 10
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_EXCERPT_CHARACTERS = 24_000
MAX_REDIRECTS = 3
SEARCH_ENDPOINT = "https://api.tavily.com/search"


class SearchError(RuntimeError):
    """Neither configured search provider produced a usable response."""


class WebPageError(ValueError):
    """The page cannot be safely fetched or does not contain readable text."""


def _aware_date(value: Any) -> str | None:
    if not isinstance(value, (str, datetime)):
        return None
    try:
        parsed = (
            value if isinstance(value, datetime)
            else datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        )
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


def _date_metadata(details: dict[str, Any]) -> dict[str, Any]:
    """Retain date meaning and provenance; never reinterpret a generic date."""
    metadata: dict[str, Any] = {}
    fields = {
        "published_at": (
            "published_at", "publication_time", "publication_date",
            "published_date", "publishedDate", "datePublished",
            "article:published_time", "og:published_time",
        ),
        "modified_at": (
            "modified_at", "last_modified", "modifiedDate", "dateModified",
            "article:modified_time", "og:modified_time",
        ),
    }
    for output, names in fields.items():
        prefix = "publication" if output == "published_at" else "modified"
        for name in names:
            raw = details.get(name)
            if not isinstance(raw, (str, datetime)) or not str(raw).strip():
                continue
            # Preserve an imprecise recorded date for display, but never turn
            # a date-only or timezone-free value into a precise timestamp.
            metadata.setdefault(f"{prefix}_field", name)
            metadata.setdefault(f"{prefix}_raw", str(raw))
            parsed = _aware_date(raw)
            if parsed is not None:
                metadata[output] = parsed
                metadata[f"{prefix}_field"] = name
                metadata[f"{prefix}_raw"] = str(raw)
                break
    return metadata


def _public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.is_global and not address.is_multicast


def _url_parts(value: str) -> tuple[str, str, int]:
    """Accept public HTTP(S) addresses without credentials or unusual ports."""
    if not isinstance(value, str) or not value.strip():
        raise WebPageError("A non-empty HTTP(S) page URL is required.")
    try:
        parts = urlsplit(value.strip())
        port = parts.port
        host = parts.hostname
    except ValueError as exc:
        raise WebPageError("The page URL is malformed.") from exc
    if parts.scheme.lower() not in {"http", "https"} or not host:
        raise WebPageError("Only HTTP(S) page URLs are supported.")
    if parts.username is not None or parts.password is not None:
        raise WebPageError("Page URLs must not include credentials.")
    if port is not None and port not in {80, 443}:
        raise WebPageError("Only standard web ports are supported.")
    try:
        host = host.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise WebPageError("The page hostname is malformed.") from exc
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise WebPageError("Local and internal page addresses are not allowed.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[a-z0-9.-]+", host):
            raise WebPageError("The page hostname is malformed.")
    else:
        if not _public_ip(host):
            raise WebPageError("The page address must be public.")
    normalized_host = f"[{host}]" if ":" in host else host
    authority = f"{normalized_host}:{port}" if port is not None else normalized_host
    normalized = urlunsplit((parts.scheme.lower(), authority, parts.path or "/", parts.query, ""))
    return normalized, host, port or (443 if parts.scheme.lower() == "https" else 80)


def _public_addresses(host: str, port: int) -> list[str]:
    try:
        entries = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise WebPageError("The page hostname could not be resolved.") from exc
    addresses = list(dict.fromkeys(entry[4][0] for entry in entries))
    if not addresses or not all(_public_ip(address) for address in addresses):
        raise WebPageError("The page hostname must resolve only to public addresses.")
    return addresses


class _PinnedHTTPSAdapter(HTTPAdapter):
    """Connect to a validated IP while retaining hostname certificate checks."""

    def __init__(self, hostname: str):
        self._hostname = hostname
        super().__init__(max_retries=0)

    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        kwargs["assert_hostname"] = self._hostname
        kwargs["server_hostname"] = self._hostname
        return super().init_poolmanager(connections, maxsize, block=block, **kwargs)


def _search_sources(results: Any, provider: str, limit: int) -> list[RetrievedSource]:
    sources: list[RetrievedSource] = []
    if not isinstance(results, list):
        return sources
    retrieved_at = datetime.now(timezone.utc).isoformat()
    seen: set[tuple[str, str]] = set()
    for result in results:
        if not isinstance(result, dict):
            continue
        url = result.get("url") or result.get("href")
        excerpt = result.get("content") or result.get("body")
        if not isinstance(excerpt, str) or not excerpt.strip():
            continue
        try:
            url, _, _ = _url_parts(url)
        except WebPageError:
            continue
        content = excerpt.strip()[:MAX_EXCERPT_CHARACTERS]
        key = (url, content)
        if key in seen:
            continue
        seen.add(key)
        metadata = {
            "title": str(result.get("title") or "").strip(),
            "provider": provider,
            "content_kind": "search_excerpt",
            "retrieved_at": retrieved_at,
            "excerpt_truncated": len(excerpt.strip()) > MAX_EXCERPT_CHARACTERS,
            **_date_metadata(result),
        }
        sources.append(RetrievedSource(content=content, source=url, metadata=metadata))
        if len(sources) >= limit:
            break
    return sources


def _duckduckgo(query: str, limit: int) -> list[RetrievedSource]:
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        # The installed provider has its own bounded HTTP timeout. Do not
        # silently leave a search running indefinitely in an advisor worker.
        results = list(DDGS(timeout=REQUEST_TIMEOUT).text(query, max_results=limit))
    except Exception as exc:
        raise SearchError("Web search failed after provider fallback.") from exc
    return _search_sources(results, "duckduckgo", limit)


def search_web(query: str, max_results: int = 3) -> list[RetrievedSource]:
    """Search Tavily when configured, otherwise use the installed DDGS provider."""
    if not isinstance(query, str) or not query.strip() or len(query.strip()) > 1000:
        raise ValueError("Search requires a non-empty query of at most 1000 characters.")
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 5:
        raise ValueError("max_results must be an integer between 1 and 5.")
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if api_key:
        try:
            response = requests.post(
                SEARCH_ENDPOINT,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": query.strip(), "search_depth": "basic",
                    "max_results": max_results, "include_answer": False,
                },
                timeout=REQUEST_TIMEOUT,
            )
            try:
                response.raise_for_status()
                data = response.json()
            finally:
                response.close()
            sources = _search_sources(data.get("results") if isinstance(data, dict) else None, "tavily", max_results)
            if sources:
                return sources
        except (requests.RequestException, ValueError):
            # Failure details can contain API credentials. The fallback error
            # exposed to an analyst deliberately contains no provider payload.
            pass
    return _duckduckgo(query.strip(), max_results)


def _page_dates(soup: BeautifulSoup) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for tag in soup.find_all("meta"):
        name = tag.get("property") or tag.get("name")
        if name in {
            "article:published_time", "og:published_time", "datePublished",
            "article:modified_time", "og:modified_time", "dateModified",
        }:
            details.setdefault(name, tag.get("content"))
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            structured = json.loads(script.string or script.get_text())
        except (ValueError, TypeError, RecursionError):
            continue
        pending = [structured]
        examined = 0
        while pending and examined < 100:
            node = pending.pop()
            examined += 1
            if isinstance(node, list):
                pending.extend(node[:100])
            elif isinstance(node, dict):
                types = node.get("@type", [])
                types = [types] if isinstance(types, str) else types
                if isinstance(types, list) and any(
                    isinstance(kind, str) and kind in {"Article", "NewsArticle", "BlogPosting", "Report", "WebPage", "SportsArticle"}
                    for kind in types
                ):
                    for name in ("datePublished", "dateModified"):
                        if name in node:
                            details.setdefault(name, node[name])
                # Avoid using a nested SportsEvent's match date as publication.
                if "@graph" in node:
                    pending.append(node["@graph"])
    return _date_metadata(details)


def _extract_page(raw: bytes, encoding: str | None, url: str) -> RetrievedSource:
    soup = BeautifulSoup(raw, "html.parser", from_encoding=encoding)
    metadata = _page_dates(soup)
    title_tag = soup.find("meta", attrs={"property": "og:title"})
    title = (
        str(title_tag.get("content") or "").strip() if title_tag is not None
        else soup.title.get_text(" ", strip=True) if soup.title is not None else ""
    )
    for tag in soup.select("script, style, nav, footer, header, aside, form, button, noscript, svg, iframe"):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    content = main.get_text("\n", strip=True)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()
    if not content:
        raise WebPageError("The page has no readable article text; it may require JavaScript or a subscription.")
    metadata.update({
        "title": title,
        "provider": "web_page",
        "content_kind": "page_excerpt",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "excerpt_truncated": len(content) > MAX_EXCERPT_CHARACTERS,
    })
    return RetrievedSource(content=content[:MAX_EXCERPT_CHARACTERS], source=url, metadata=metadata)


def read_web_page(url: str) -> RetrievedSource:
    """Read a bounded public HTML/text page, checking every redirect destination.

    Validated DNS addresses are pinned for each request; the original hostname
    remains the Host header and TLS identity. Environment proxies and cookies
    are disabled so arbitrary page links cannot reach local services indirectly.
    """
    current, _, _ = _url_parts(url)
    deadline = time.monotonic() + REQUEST_TIMEOUT

    def remaining_time() -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WebPageError("The page exceeded the 10 second reading budget.")
        return remaining

    for redirect in range(MAX_REDIRECTS + 1):
        remaining_time()
        current, host, port = _url_parts(current)
        address = _public_addresses(host, port)[0]
        remaining_time()
        parts = urlsplit(current)
        pinned_host = f"[{address}]" if ":" in address else address
        pinned_url = urlunsplit((parts.scheme, f"{pinned_host}:{port}", parts.path, parts.query, ""))
        try:
            with requests.Session() as session:
                session.trust_env = False
                if parts.scheme == "https":
                    session.mount("https://", _PinnedHTTPSAdapter(host))
                with session.get(
                    pinned_url,
                    headers={"Host": parts.netloc, "User-Agent": "FootballStrategyAdvisor/1.0", "Accept": "text/html, text/plain"},
                    allow_redirects=False,
                    stream=True,
                    timeout=remaining_time(),
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location or redirect == MAX_REDIRECTS:
                            raise WebPageError("The page redirected too many times or omitted its destination.")
                        current = urljoin(current, location)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                    if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                        raise WebPageError("Only HTML or plain-text pages can be read; PDF and binary documents are unsupported.")
                    try:
                        size = int(response.headers.get("Content-Length", "0"))
                    except ValueError:
                        size = 0
                    if size > MAX_PAGE_BYTES:
                        raise WebPageError("The page exceeds the 2 MB download limit.")
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_content(chunk_size=16_384):
                        remaining_time()
                        total += len(chunk)
                        if total > MAX_PAGE_BYTES:
                            raise WebPageError("The page exceeds the 2 MB download limit.")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                    remaining_time()
                    if content_type == "text/plain":
                        text = raw.decode(response.encoding or "utf-8", errors="replace").strip()
                        if not text:
                            raise WebPageError("The page contains no readable text.")
                        return RetrievedSource(content=text[:MAX_EXCERPT_CHARACTERS], source=current, metadata={
                            "title": "", "provider": "web_page", "content_kind": "page_excerpt",
                            "retrieved_at": datetime.now(timezone.utc).isoformat(),
                            "excerpt_truncated": len(text) > MAX_EXCERPT_CHARACTERS,
                        })
                    encoding = response.encoding
                    # Requests guesses ISO-8859-1 for text/html lacking charset;
                    # let BeautifulSoup inspect HTML declarations in that case.
                    if "charset=" not in response.headers.get("Content-Type", "").lower():
                        encoding = None
                    return _extract_page(raw, encoding, current)
        except requests.RequestException as exc:
            raise WebPageError("The page could not be downloaded within the web request limits.") from exc
    raise WebPageError("The page could not be read.")
