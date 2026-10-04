from tests.conftest import PROFILE


def test_analysis_is_outdated_after_profile_change(client, ready_user):
    r = client.post("/api/recommendations", headers=ready_user)
    assert r.status_code == 201
    assert r.json()["outdated"] is False
    assert client.get("/api/recommendations/latest", headers=ready_user).json()["outdated"] is False

    changed = {**PROFILE, "risk_tolerance": 5}
    assert client.put("/api/profile", json=changed, headers=ready_user).status_code == 200

    assert client.get("/api/recommendations/latest", headers=ready_user).json()["outdated"] is True

    # regenerating clears the flag
    assert client.post("/api/recommendations", headers=ready_user).json()["outdated"] is False
    assert client.get("/api/recommendations/latest", headers=ready_user).json()["outdated"] is False
