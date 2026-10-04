def test_history_lists_and_retrieves_all_analyses(client, ready_user):
    ids = [client.post("/api/recommendations", headers=ready_user).json()["id"] for _ in range(2)]

    r = client.get("/api/recommendations", headers=ready_user)
    assert r.status_code == 200
    items = r.json()
    assert [i["id"] for i in items] == sorted(ids, reverse=True)  # newest first
    assert set(items[0]) == {"id", "created_at", "mode", "outdated"}

    for i in ids:
        one = client.get(f"/api/recommendations/{i}", headers=ready_user)
        assert one.status_code == 200 and one.json()["id"] == i
        assert one.json()["analysis"]["recommendations"] and one.json()["disclaimer"]

    # "latest" is still routed correctly alongside /{id}
    assert client.get("/api/recommendations/latest", headers=ready_user).json()["id"] == max(ids)


def test_cannot_read_another_users_analysis(client, ready_user):
    rec_id = client.post("/api/recommendations", headers=ready_user).json()["id"]
    r = client.post("/api/auth/signup", json={"email": "other@example.com", "password": "password123"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get(f"/api/recommendations/{rec_id}", headers=other).status_code == 404
    assert client.get("/api/recommendations", headers=other).json() == []
