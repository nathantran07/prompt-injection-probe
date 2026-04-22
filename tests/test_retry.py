"""Tests for probe.post_with_retry and probe.judge_with_retry."""
from __future__ import annotations

import httpx
import pytest

import probe


class _FakeResponse:
    def __init__(self, status_code: int, headers: dict[str, str] | None = None, json_body: dict | None = None):
        self.status_code = status_code
        self.headers = headers or {}
        self._json = json_body or {}

    def json(self) -> dict:
        return self._json


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Never actually sleep during retry tests."""
    monkeypatch.setattr(probe.time, "sleep", lambda _s: None)


def test_post_returns_200_immediately(monkeypatch):
    calls: list[dict] = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeResponse(200, json_body={"response": "ok"})

    monkeypatch.setattr(probe.httpx, "post", fake_post)
    resp = probe.post_with_retry("http://x/chat", "hello")
    assert resp.status_code == 200
    assert len(calls) == 1
    assert calls[0]["json"] == {"message": "hello"}
    assert calls[0]["timeout"] == 30.0


def test_post_retries_once_on_429_then_succeeds(monkeypatch):
    responses = [
        _FakeResponse(429, headers={"Retry-After": "1"}),
        _FakeResponse(200, json_body={"response": "ok"}),
    ]
    def fake_post(url, json, timeout):
        return responses.pop(0)
    monkeypatch.setattr(probe.httpx, "post", fake_post)

    resp = probe.post_with_retry("http://x/chat", "hello")
    assert resp.status_code == 200
    assert responses == []  # both consumed


def test_post_returns_429_after_second_attempt(monkeypatch):
    def fake_post(url, json, timeout):
        return _FakeResponse(429, headers={"Retry-After": "1"})
    monkeypatch.setattr(probe.httpx, "post", fake_post)

    resp = probe.post_with_retry("http://x/chat", "hello")
    assert resp.status_code == 429


def test_post_uses_default_retry_after_when_header_missing(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(probe.time, "sleep", lambda s: sleeps.append(s))

    responses = [_FakeResponse(429, headers={}), _FakeResponse(200)]
    def fake_post(url, json, timeout):
        return responses.pop(0)
    monkeypatch.setattr(probe.httpx, "post", fake_post)

    probe.post_with_retry("http://x/chat", "hi")
    assert sleeps == [10]  # DEFAULT_RETRY_AFTER


def test_post_propagates_connect_error(monkeypatch):
    def fake_post(url, json, timeout):
        raise httpx.ConnectError("boom")
    monkeypatch.setattr(probe.httpx, "post", fake_post)

    with pytest.raises(httpx.ConnectError):
        probe.post_with_retry("http://x/chat", "hi")


# --- judge_with_retry ---


class _FakeTextBlock:
    type = "text"
    def __init__(self, text: str):
        self.text = text


class _FakeMessage:
    def __init__(self, text: str):
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    def __init__(self, script):
        self._script = list(script)

    def create(self, **_kwargs):
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class _FakeClient:
    def __init__(self, script):
        self.messages = _FakeMessages(script)


def _api_status_error(status_code: int, retry_after: str | None = "1"):
    """Build a real anthropic.APIStatusError instance."""
    from anthropic import APIStatusError
    headers = {"retry-after": retry_after} if retry_after is not None else {}
    fake_resp = httpx.Response(
        status_code=status_code,
        headers=headers,
        request=httpx.Request("POST", "http://fake"),
    )
    return APIStatusError("rate limited", response=fake_resp, body=None)


def test_judge_returns_text_on_success():
    client = _FakeClient([_FakeMessage('{"result": "BLOCKED", "reason": "ok"}')])
    out = probe.judge_with_retry(client, "prompt")
    assert out == '{"result": "BLOCKED", "reason": "ok"}'


def test_judge_retries_once_on_429_then_succeeds():
    client = _FakeClient([
        _api_status_error(429, retry_after="1"),
        _FakeMessage("ok"),
    ])
    out = probe.judge_with_retry(client, "prompt")
    assert out == "ok"


def test_judge_raises_after_second_429():
    from anthropic import APIStatusError
    client = _FakeClient([
        _api_status_error(429),
        _api_status_error(429),
    ])
    with pytest.raises(APIStatusError):
        probe.judge_with_retry(client, "prompt")
