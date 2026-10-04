import pytest

from app.advisor import SYSTEM_PROMPT, build_user_message
from app.models import User
from app.portfolio import build_portfolio

from .conftest import PROFILE

NEW = ("investment_knowledge", "investment_experience_years", "max_acceptable_loss_pct")


def test_profile_roundtrips_new_fields(client, auth):
    r = client.put("/api/profile", json=PROFILE, headers=auth)
    assert r.status_code == 200
    for k in NEW:
        assert r.json()[k] == PROFILE[k]


@pytest.mark.parametrize("field", NEW)
def test_profile_requires_new_fields(client, auth, field):
    body = {k: v for k, v in PROFILE.items() if k != field}
    assert client.put("/api/profile", json=body, headers=auth).status_code == 422


@pytest.mark.parametrize("patch", [
    {"investment_knowledge": "expert"}, {"investment_experience_years": 51},
    {"investment_experience_years": -1}, {"max_acceptable_loss_pct": 15},
])
def test_profile_validates_new_fields(client, auth, patch):
    assert client.put("/api/profile", json={**PROFILE, **patch}, headers=auth).status_code == 422


@pytest.mark.parametrize("field", NEW)
def test_recommendations_400_when_suitability_incomplete(client, ready_user, db_session_factory, field):
    db = db_session_factory()
    user = db.query(User).one()
    setattr(user.profile, field, None)
    db.commit()
    db.close()
    r = client.post("/api/recommendations", headers=ready_user)
    assert r.status_code == 400
    assert r.json()["detail"] == "Complete your risk profile first"


def test_recommendations_ok_when_complete(client, ready_user):
    assert client.post("/api/recommendations", headers=ready_user).status_code == 201


def test_advisor_input_contains_suitability_fields(client, ready_user, db_session_factory):
    db = db_session_factory()
    user = db.query(User).one()
    msg = build_user_message(user, build_portfolio(user))
    db.close()
    for k in NEW:
        assert f'"{k}": {PROFILE[k]!r}'.replace("'", '"') in msg


def test_system_prompt_has_suitability_rules():
    assert "suitability statement" in SYSTEM_PROMPT
    assert "UCITS ETFs or bond funds" in SYSTEM_PROMPT


def test_legacy_profile_without_new_fields_is_readable(client, auth, db_session_factory):
    from app.models import RiskProfile

    db = db_session_factory()
    uid = db.query(User).one().id
    db.add(RiskProfile(user_id=uid, age=40, annual_income=1, savings_goal="other", monthly_investment=1,
                       risk_tolerance=2, horizon_years=5))
    db.commit()
    db.close()
    r = client.get("/api/auth/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["profile"]["investment_knowledge"] is None
