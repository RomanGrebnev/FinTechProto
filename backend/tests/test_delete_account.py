from sqlalchemy import text

from app.db import Base


def _rows(session_factory, user_id):
    """Count rows referencing the user across every table."""
    db = session_factory()
    try:
        total = 0
        for table in Base.metadata.sorted_tables:
            if table.name == "users":
                total += db.execute(text("select count(*) from users where id = :i"), {"i": user_id}).scalar()
            elif "user_id" in table.c:
                total += db.execute(text(f"select count(*) from {table.name} where user_id = :i"), {"i": user_id}).scalar()
        return total
    finally:
        db.close()


def test_delete_account_removes_all_data(client, ready_user, db_session_factory):
    client.post("/api/recommendations", headers=ready_user)
    client.post("/api/recommendations", headers=ready_user)
    uid = client.get("/api/auth/me", headers=ready_user).json()["id"]
    assert _rows(db_session_factory, uid) >= 5  # user, profile, holding, 2 recommendations

    r = client.request("DELETE", "/api/auth/me", json={"password": "password123"}, headers=ready_user)
    assert r.status_code == 204
    assert _rows(db_session_factory, uid) == 0
    assert client.get("/api/auth/me", headers=ready_user).status_code == 401


def test_delete_account_requires_correct_password(client, ready_user):
    r = client.request("DELETE", "/api/auth/me", json={"password": "wrong-password"}, headers=ready_user)
    assert r.status_code == 403
    assert client.get("/api/auth/me", headers=ready_user).status_code == 200
