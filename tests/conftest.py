import os

# Use an in-memory SQLite DB for tests, set BEFORE importing the app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import fakeredis
import pytest

import app as app_module


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Replace the real Redis with an in-memory fake for every test."""
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(app_module, "r", fake)
    yield fake
    fake.flushall()


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.app_context():
        app_module.db.drop_all()
        app_module.db.create_all()
    return app_module.app.test_client()
