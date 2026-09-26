"""Offline checks for attributable search results and bounded public page reads."""

import json
import socket
from datetime import datetime

import pytest
import requests

from src.advisor import search


class Response:
    def __init__(self, text="", *, status=200, headers=None, payload=None, chunks=None):
        self.status_code = status
        self.headers = {"Content-Type": "text/html; charset=utf-8", **(headers or {})}
        self.encoding = "utf-8"
        self.raw_bytes = text.encode("utf-8")
        self.payload = payload
        self.chunks = chunks
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.closed = True

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("Provider failed.")

    def json(self):
        return self.payload

    def iter_content(self, chunk_size):
        if self.chunks is not None:
            yield from self.chunks
        else:
            yield self.raw_bytes


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("An offline search test attempted network access.")

    monkeypatch.setattr(requests, "post", forbidden)
    monkeypatch.setattr(requests.Session, "get", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(search, "_duckduckgo", forbidden)


def page_reader(monkeypatch, responses, *, addresses=("93.184.216.34",)):
    calls = []
    sessions = []
    pending = iter(responses)

    def resolve(host, port, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port)) for address in addresses]

    class Session:
        def __init__(self):
            self.trust_env = True
            self.adapters = {}
            sessions.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def mount(self, prefix, adapter):
            self.adapters[prefix] = adapter

        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return next(pending)

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(requests, "Session", Session)
    return calls, sessions


def test_tavily_preserves_individual_excerpts_and_never_generated_answer(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    captured = {}
    response = Response(payload={
        "answer": "Unsupported provider-generated answer.",
        "results": [{
            "url": "https://club.example/news#article", "title": "Club news",
            "content": "The club announced a signing, subject to medical clearance.",
            "published_at": "2026-08-01T14:00:00+02:00",
        }],
    })

    def post(url, **kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr(requests, "post", post)
    sources = search.search_web("confirmed club signing")
    assert len(sources) == 1
    assert "subject to medical clearance" in sources[0].content
    assert "Unsupported provider" not in sources[0].content
    assert sources[0].source == "https://club.example/news"
    assert sources[0].metadata["published_at"] == "2026-08-01T12:00:00+00:00"
    assert sources[0].metadata["publication_field"] == "published_at"
    assert sources[0].metadata["content_kind"] == "search_excerpt"
    assert datetime.fromisoformat(sources[0].metadata["retrieved_at"]).utcoffset() is not None
    assert captured["json"]["include_answer"] is False
    assert captured["timeout"] == 10
    assert response.closed


def test_search_without_api_key_calls_fallback(monkeypatch):
    recorded = []
    monkeypatch.setattr(search, "_duckduckgo", lambda query, limit: recorded.append((query, limit)) or [])
    assert search.search_web("  team tactics  ", 2) == []
    assert recorded == [("team tactics", 2)]


def test_tavily_http_failure_falls_back_without_exposing_error(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-secret")

    def broken(*args, **kwargs):
        raise requests.Timeout("A failure containing test-secret")

    monkeypatch.setattr(requests, "post", broken)
    monkeypatch.setattr(search, "_duckduckgo", lambda query, limit: [])
    assert search.search_web("club transfer") == []


def test_tavily_answer_without_sources_falls_back(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: Response(payload={"answer": "Nothing attributable"}))
    calls = []
    monkeypatch.setattr(search, "_duckduckgo", lambda query, limit: calls.append(query) or [])
    assert search.search_web("transfer evidence") == []
    assert calls == ["transfer evidence"]


@pytest.mark.parametrize("query, limit", [("", 3), (" " * 10, 3), ("q" * 1001, 3), ("x", 0), ("x", 6), ("x", True)])
def test_search_arguments_are_bounded(query, limit):
    with pytest.raises(ValueError):
        search.search_web(query, limit)


def test_provider_deduplicates_and_skips_missing_or_unsafe_sources():
    results = [
        {"href": "https://club.example/a", "body": "A dated announcement.", "title": "A"},
        {"href": "https://club.example/a#top", "body": "A dated announcement."},
        {"href": "https://club.example/empty", "body": ""},
        {"href": "http://127.0.0.1/a", "body": "Private"},
        {"href": "https://name:secret@club.example/a", "body": "Credentials"},
        {"href": "https://club.example/b", "body": "B excerpt."},
    ]
    sources = search._search_sources(results, "duckduckgo", 3)
    assert [source.source for source in sources] == ["https://club.example/a", "https://club.example/b"]


def test_ddgs_uses_real_excerpt_fields_and_timeout(monkeypatch):
    import ddgs

    captured = {}

    class DDGS:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def text(self, query, **kwargs):
            captured.update(query=query, **kwargs)
            return [{"href": "https://news.example/a", "title": "News", "body": "Article excerpt."}]

    monkeypatch.setattr(ddgs, "DDGS", DDGS)
    # The autouse fixture blocks _duckduckgo; exercise the real implementation
    # captured before that fixture replaces it.
    sources = REAL_DUCKDUCKGO("a transfer question", 2)
    assert captured == {"timeout": 10, "query": "a transfer question", "max_results": 2}
    assert sources[0].content == "Article excerpt."
    assert sources[0].metadata["provider"] == "duckduckgo"


REAL_DUCKDUCKGO = search._duckduckgo


def test_dates_keep_provenance_and_do_not_invent_timezone_or_publication():
    metadata = search._date_metadata({
        "date": "2026-01-01T00:00:00Z",
        "publication_date": "2026-01-02",
        "dateModified": "2026-01-03T18:00:00Z",
    })
    assert "published_at" not in metadata
    assert metadata["publication_raw"] == "2026-01-02"
    assert metadata["publication_field"] == "publication_date"
    assert metadata["modified_at"] == "2026-01-03T18:00:00+00:00"


def test_page_retains_qualifications_and_explicit_article_dates(monkeypatch):
    html = """<html><head><title>Transfer report</title>
        <meta property="article:published_time" content="2026-08-05T13:00:00Z">
        <script type="application/ld+json">{"@type":"NewsArticle","dateModified":"2026-08-06T12:00:00+02:00"}</script>
        </head><body><nav>Unrelated navigation</nav><article><h1>Report</h1>
        <p>The club discussed a transfer.</p><p>No agreement has been reached.</p>
        <p>The reported price is an estimate.</p></article><footer>Unrelated footer</footer></body></html>"""
    response = Response(html)
    calls, sessions = page_reader(monkeypatch, [response])
    source = search.read_web_page("https://news.example/transfer")
    assert source.source == "https://news.example/transfer"
    assert "No agreement has been reached." in source.content
    assert "price is an estimate" in source.content
    assert "Unrelated" not in source.content
    assert source.metadata["title"] == "Transfer report"
    assert source.metadata["published_at"] == "2026-08-05T13:00:00+00:00"
    assert source.metadata["publication_field"] == "article:published_time"
    assert source.metadata["modified_at"] == "2026-08-06T10:00:00+00:00"
    assert calls[0][0] == "https://93.184.216.34:443/transfer"
    assert calls[0][1]["headers"]["Host"] == "news.example"
    assert calls[0][1]["allow_redirects"] is False
    assert 0 < calls[0][1]["timeout"] <= 10
    assert sessions[0].trust_env is False
    adapter = sessions[0].adapters["https://"]
    assert adapter.poolmanager.connection_pool_kw["assert_hostname"] == "news.example"
    assert adapter.poolmanager.connection_pool_kw["server_hostname"] == "news.example"
    assert response.closed


def test_jsonld_graph_dates_do_not_use_match_event_date(monkeypatch):
    data = {"@graph": [
        {"@type": "SportsEvent", "datePublished": "2026-08-01T00:00:00Z", "startDate": "2026-08-02"},
        {"@type": "NewsArticle", "datePublished": "2026-08-03T18:00:00Z"},
    ]}
    html = f'<script type="application/ld+json">{json.dumps(data)}</script><main>Published match review.</main>'
    page_reader(monkeypatch, [Response(html)])
    source = search.read_web_page("http://news.example/review")
    assert source.metadata["published_at"] == "2026-08-03T18:00:00+00:00"


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://news.example/a", "http://localhost/a",
    "http://team.local/a", "http://127.0.0.1/a", "http://169.254.169.254/metadata",
    "http://10.0.0.1/a", "http://[::1]/a", "http://[::ffff:127.0.0.1]/a",
    "http://224.0.0.1/a", "https://name:secret@news.example/a", "http://news.example:8080/a",
])
def test_unsafe_page_urls_are_rejected_without_fetch(url):
    with pytest.raises(search.WebPageError):
        search.read_web_page(url)


def test_dns_with_any_private_address_is_rejected(monkeypatch):
    calls, _ = page_reader(monkeypatch, [], addresses=("93.184.216.34", "192.168.1.1"))
    with pytest.raises(search.WebPageError, match="only to public"):
        search.read_web_page("https://news.example/a")
    assert calls == []


def test_redirect_to_private_address_is_rejected(monkeypatch):
    response = Response(status=302, headers={"Location": "http://169.254.169.254/latest/meta-data/"})
    calls, _ = page_reader(monkeypatch, [response])
    with pytest.raises(search.WebPageError, match="must be public"):
        search.read_web_page("https://news.example/a")
    assert len(calls) == 1
    assert response.closed


def test_redirect_dns_is_revalidated_and_final_url_is_preserved(monkeypatch):
    responses = [Response(status=302, headers={"Location": "/final"}), Response("<main>Final article.</main>")]
    calls, _ = page_reader(monkeypatch, responses)
    source = search.read_web_page("https://news.example/start")
    assert source.source == "https://news.example/final"
    assert [call[0] for call in calls] == ["https://93.184.216.34:443/start", "https://93.184.216.34:443/final"]
    assert all(response.closed for response in responses)


def test_redirect_loop_is_bounded(monkeypatch):
    calls, _ = page_reader(monkeypatch, [Response(status=302, headers={"Location": "/again"}) for _ in range(4)])
    with pytest.raises(search.WebPageError, match="too many times"):
        search.read_web_page("https://news.example/a")
    assert len(calls) == 4


@pytest.mark.parametrize("content_type", ["application/pdf", "application/octet-stream", "image/png", ""])
def test_unsupported_page_content_is_rejected(monkeypatch, content_type):
    page_reader(monkeypatch, [Response(headers={"Content-Type": content_type})])
    with pytest.raises(search.WebPageError, match="HTML or plain-text"):
        search.read_web_page("https://news.example/document")


def test_page_size_is_checked_before_and_during_download(monkeypatch):
    page_reader(monkeypatch, [Response(headers={"Content-Length": str(search.MAX_PAGE_BYTES + 1)})])
    with pytest.raises(search.WebPageError, match="2 MB"):
        search.read_web_page("https://news.example/a")
    page_reader(monkeypatch, [Response(chunks=[b"x" * search.MAX_PAGE_BYTES, b"x"])])
    with pytest.raises(search.WebPageError, match="2 MB"):
        search.read_web_page("https://news.example/a")


def test_plain_text_is_returned_without_parsing_as_html(monkeypatch):
    page_reader(monkeypatch, [Response("Player A < Player B is a comparison, not HTML.", headers={"Content-Type": "text/plain"})])
    source = search.read_web_page("https://stats.example/comparison.txt")
    assert source.content == "Player A < Player B is a comparison, not HTML."
    assert source.metadata["content_kind"] == "page_excerpt"
    assert "published_at" not in source.metadata


def test_page_excerpt_truncation_is_disclosed(monkeypatch):
    page_reader(monkeypatch, [Response("<article>" + "x" * (search.MAX_EXCERPT_CHARACTERS + 1) + "</article>")])
    source = search.read_web_page("https://news.example/a")
    assert len(source.content) == search.MAX_EXCERPT_CHARACTERS
    assert source.metadata["excerpt_truncated"] is True


def test_page_without_readable_text_reports_failure(monkeypatch):
    page_reader(monkeypatch, [Response("<script>Secret content loaded only by JavaScript.</script>")])
    with pytest.raises(search.WebPageError, match="no readable"):
        search.read_web_page("https://news.example/a")


def test_page_reading_budget_is_checked_between_download_chunks(monkeypatch):
    page_reader(monkeypatch, [Response(chunks=[b"<main>Article.", b"</main>"])])
    clock_values = iter([0, 0, 0, 0, 0, 11])
    monkeypatch.setattr(search.time, "monotonic", lambda: next(clock_values))
    with pytest.raises(search.WebPageError, match="10 second"):
        search.read_web_page("https://news.example/a")


def test_jsonld_with_malformed_type_does_not_break_page_extraction(monkeypatch):
    page_reader(monkeypatch, [Response('<script type="application/ld+json">{"@type":[{"bad":"type"}]}</script><main>Readable article.</main>')])
    assert search.read_web_page("https://news.example/a").content == "Readable article."
