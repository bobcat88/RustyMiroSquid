import pytest
import httpx
from httpx import Response, Request

from app.utils.url_fetcher import _safe_get, fetch_url_text, MAX_RESPONSE_BYTES

def test_safe_get_success(httpx_mock):
    httpx_mock.add_response(url="http://example.com", status_code=200, content=b"Hello")
    
    resp = _safe_get("http://example.com", headers={"User-Agent": "test"}, timeout=5)
    assert resp.status_code == 200
    assert resp.content == b"Hello"

def test_safe_get_redirect(httpx_mock):
    httpx_mock.add_response(url="http://example.com", status_code=301, headers={"location": "http://example.com/target"})
    httpx_mock.add_response(url="http://example.com/target", status_code=200, content=b"Redirected!")
    
    resp = _safe_get("http://example.com", headers={"User-Agent": "test"}, timeout=5)
    assert resp.status_code == 200
    assert resp.content == b"Redirected!"

def test_safe_get_too_large(httpx_mock):
    # Simulate a response that is too large
    heavy_content = b"a" * (MAX_RESPONSE_BYTES + 1024)
    httpx_mock.add_response(url="http://example.com", status_code=200, content=heavy_content)
    
    with pytest.raises(ValueError, match="Response exceeds .* MB size limit"):
        _safe_get("http://example.com", headers={}, timeout=5)

def test_fetch_url_html(httpx_mock):
    html = b"<html><head><title>Test</title></head><body><h1>Hello</h1><p>World. " + b"This is a padding text to ensure that the extracted text is at least one hundred characters long. Otherwise the url_fetcher will throw an error." * 3 + b"</p></body></html>"
    httpx_mock.add_response(url="http://example.com", status_code=200, content=html, headers={"Content-Type": "text/html"})
    
    result = fetch_url_text("http://example.com")
    assert "Hello" in result["text"]
    assert "World" in result["text"]

def test_fetch_url_network_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("Connection failed"), url="http://example.com")
    
    with pytest.raises(httpx.RequestError):
        fetch_url_text("http://example.com")

def test_fetch_url_invalid_ip():
    with pytest.raises(ValueError, match="internal addresses"):
        fetch_url_text("http://127.0.0.1")
        
def test_fetch_url_invalid_scheme():
    with pytest.raises(ValueError, match="Only http and https URLs are supported"):
        fetch_url_text("ftp://example.com")
