"""Notifier : best-effort, ne leve jamais, respecte enabled/token/chat_id."""
import bot.notify as notify
from bot.notify import Notifier, esc


class _Resp:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


def test_disabled_without_token():
    n = Notifier(None, None, enabled=True)
    assert n.enabled is False
    assert n.send("coucou") is False          # no-op, pas d'exception


def test_disabled_when_flag_off():
    n = Notifier("tok", "123", enabled=False)
    assert n.enabled is False
    assert n.send("x") is False


def test_send_builds_request(monkeypatch):
    calls = {}

    def fake_post(url, data=None, files=None, timeout=None):
        calls["url"] = url
        calls["data"] = data
        calls["files"] = files
        return _Resp(200)

    monkeypatch.setattr(notify.requests, "post", fake_post)
    n = Notifier("SECRET", "42", enabled=True)
    assert n.send("<b>hi</b>") is True
    assert calls["url"].endswith("/botSECRET/sendMessage")
    assert calls["data"]["chat_id"] == "42"
    assert calls["data"]["parse_mode"] == "HTML"


def test_http_error_returns_false(monkeypatch):
    monkeypatch.setattr(notify.requests, "post", lambda *a, **k: _Resp(403, "forbidden"))
    n = Notifier("t", "c", enabled=True)
    assert n.send("x") is False


def test_network_exception_swallowed(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no network")

    monkeypatch.setattr(notify.requests, "post", boom)
    n = Notifier("t", "c", enabled=True)
    assert n.send("x") is False               # avale l'exception


def test_send_photo_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(notify.requests, "post", lambda *a, **k: _Resp(200))
    n = Notifier("t", "c", enabled=True)
    assert n.send_photo(tmp_path / "nope.png") is False


def test_esc():
    assert esc("a<b>&c") == "a&lt;b&gt;&amp;c"
