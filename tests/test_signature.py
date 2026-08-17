import hashlib
import hmac

from app.main import verify_signature

SECRET = "test-secret"


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def test_verify_signature_accepts_valid(monkeypatch):
    from app import main as main_mod
    monkeypatch.setattr(main_mod.settings, "github_webhook_secret", SECRET)
    body = b'{"foo": "bar"}'
    assert verify_signature(body, _sign(body)) is True


def test_verify_signature_rejects_wrong_signature(monkeypatch):
    from app import main as main_mod
    monkeypatch.setattr(main_mod.settings, "github_webhook_secret", SECRET)
    body = b'{"foo": "bar"}'
    assert verify_signature(body, "sha256=abcdef1234") is False


def test_verify_signature_rejects_wrong_prefix(monkeypatch):
    from app import main as main_mod
    monkeypatch.setattr(main_mod.settings, "github_webhook_secret", SECRET)
    body = b"anything"
    assert verify_signature(body, "sha1=whatever") is False


def test_verify_signature_rejects_empty_header(monkeypatch):
    from app import main as main_mod
    monkeypatch.setattr(main_mod.settings, "github_webhook_secret", SECRET)
    assert verify_signature(b"anything", "") is False
