import importlib


def test_dashboard_token_is_loaded_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DASHBOARD_TOKEN", "loaded-from-env-xyz")
    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "wh-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    # Point env_file somewhere empty so .env doesn't stomp on our env vars.
    monkeypatch.setenv("_PYDANTIC_DUMMY", "1")

    from app import config as config_mod
    importlib.reload(config_mod)

    assert config_mod.settings.dashboard_token == "loaded-from-env-xyz"
    assert config_mod.settings.github_app_id == "12345"
    assert config_mod.settings.github_webhook_secret == "wh-secret"

    # Reload again with the env var removed to make sure we don't pollute the
    # rest of the test session with our overrides.
    monkeypatch.delenv("DASHBOARD_TOKEN")
    importlib.reload(config_mod)


def test_dashboard_token_defaults_empty(monkeypatch):
    monkeypatch.delenv("DASHBOARD_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "wh-secret")

    from app import config as config_mod
    importlib.reload(config_mod)

    assert config_mod.settings.dashboard_token == ""
