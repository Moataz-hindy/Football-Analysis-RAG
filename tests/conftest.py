import os
import socket

import httpx
import psycopg2
import pytest
import requests

# Sanitize SSL_CERT_FILE on Windows if Anaconda sets it to a non-existent path
ssl_cert = os.environ.get("SSL_CERT_FILE")
if ssl_cert and not os.path.exists(ssl_cert):
    os.environ.pop("SSL_CERT_FILE", None)


@pytest.fixture(autouse=True)
def forbid_live_services(monkeypatch):
    """Unit tests must not spend API quota or access a developer's database."""
    original_send = httpx.Client.send

    def blocked(*args, **kwargs):
        pytest.fail("Live I/O is disabled in tests; mock the service explicitly.")

    def blocked_send(self, request, *args, **kwargs):
        if getattr(request, "url", None) and request.url.host == "testserver":
            return original_send(self, request, *args, **kwargs)
        pytest.fail("Live I/O is disabled in tests; mock the service explicitly.")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)

    monkeypatch.setattr(httpx.Client, "send", blocked_send)
    monkeypatch.setattr(psycopg2, "connect", blocked)

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
