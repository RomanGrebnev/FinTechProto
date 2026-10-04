import os

# Must be set before the app is imported (config reads the environment at import time).
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-0123456789")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("MISTRAL_API_KEY", "")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Never hit Yahoo Finance / Mistral from tests."""
    monkeypatch.setattr("app.portfolio.get_quotes", lambda symbols: {})


@pytest.fixture()
def db_session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False)


@pytest.fixture()
def client(db_session_factory):
    def override():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth(client):
    """Sign up a user and return (headers, email)."""
    email = "user@example.com"
    r = client.post("/api/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


PROFILE = {
    "age": 35, "annual_income": 50000, "savings_goal": "wealth_growth",
    "monthly_investment": 300, "risk_tolerance": 3, "horizon_years": 10,
    "investment_knowledge": "basic", "investment_experience_years": 3, "max_acceptable_loss_pct": 20,
}


@pytest.fixture()
def ready_user(client, auth):
    """User with a profile and one holding, ready to generate analyses (demo mode, no network)."""
    assert client.put("/api/profile", json=PROFILE, headers=auth).status_code == 200
    r = client.post("/api/portfolio/holdings", json={"ticker": "AAPL", "quantity": 1, "avg_buy_price": 100}, headers=auth)
    assert r.status_code in (200, 201), r.text
    return auth
