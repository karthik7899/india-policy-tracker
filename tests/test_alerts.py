"""Tests for failure alerting (alerts.py)."""

import email
import os
import sys
from email.header import decode_header, make_header

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import alerts  # noqa: E402

_ENV = {
    "RECEIVER_EMAIL": "owner@example.com, second@example.com",
    "SMTP_SERVER": "smtp.example.com",
    "SMTP_PORT": "587",
    "SMTP_USERNAME": "bot@example.com",
    "SMTP_PASSWORD": "secret",
    "RUN_URL": "https://github.com/o/r/actions/runs/123",
    "RUN_NUMBER": "95",
    "RUN_SHA": "abcdef1234567890",
}


class _FakeSMTP:
    """Records what would have been sent."""

    instances = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port
        self.started_tls = False
        self.logged_in = None
        self.sent = None
        _FakeSMTP.instances.append(self)

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def sendmail(self, sender, receivers, body):
        self.sent = (sender, receivers, body)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch(monkeypatch, env=None, ssl=False):
    _FakeSMTP.instances = []
    for key in list(_ENV) + ["SMTP_SERVER"]:
        monkeypatch.delenv(key, raising=False)
    for key, value in (env if env is not None else _ENV).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(alerts.smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setattr(alerts.smtplib, "SMTP_SSL", _FakeSMTP)


def test_sends_to_every_configured_recipient(monkeypatch):
    _patch(monkeypatch)
    assert alerts.send_failure_alert() is True
    smtp = _FakeSMTP.instances[0]
    assert smtp.started_tls is True  # port 587
    assert smtp.logged_in == ("bot@example.com", "secret")
    sender, receivers, raw = smtp.sent
    assert receivers == ["owner@example.com", "second@example.com"]
    # Non-ASCII content means the wire format is base64; read what arrives.
    message = email.message_from_string(raw)
    body = message.get_payload(decode=True).decode("utf-8")
    subject = str(make_header(decode_header(message["Subject"])))
    # The alert has to carry enough to act on without opening GitHub first.
    assert "run FAILED" in subject
    assert "actions/runs/123" in body
    assert "abcdef1" in body
    assert "Run health:" in body


def test_implicit_tls_port_skips_starttls(monkeypatch):
    _patch(monkeypatch, env={**_ENV, "SMTP_PORT": "465"})
    assert alerts.send_failure_alert() is True
    assert _FakeSMTP.instances[0].started_tls is False


def test_missing_configuration_is_not_an_error(monkeypatch):
    _patch(monkeypatch, env={k: v for k, v in _ENV.items() if k != "SMTP_SERVER"})
    assert alerts.send_failure_alert() is False
    assert _FakeSMTP.instances == []


def test_smtp_failure_never_propagates(monkeypatch):
    """The alert must not mask the failure it exists to report."""
    _patch(monkeypatch)

    def explode(*a, **kw):
        raise OSError("network unreachable")

    monkeypatch.setattr(alerts.smtplib, "SMTP", explode)
    assert alerts.send_failure_alert() is False


def test_uses_only_the_standard_library():
    """The failure being reported may be the dependency install itself."""
    source = open(
        os.path.join(os.path.dirname(__file__), "..", "alerts.py"), encoding="utf-8"
    ).read()
    for banned in ("import requests", "from logger", "import aiohttp", "from config"):
        assert banned not in source, f"alerts.py must not depend on {banned!r}"
