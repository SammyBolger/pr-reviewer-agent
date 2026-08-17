import os

# Set fake secrets before app.config is imported by tests, so tests don't need
# a real .env or real API keys.
os.environ.setdefault("GITHUB_APP_ID", "0")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("GITHUB_APP_PRIVATE_KEY_PATH", "/tmp/nonexistent.pem")
