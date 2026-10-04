import pathlib

from app import config


def test_disclosure_states_cif_status():
    d = config.DISCLAIMER
    assert config.CIF_ORIAS_NUMBER in d
    assert "CIF" in d and "non-independent" in d
    assert "information you provided" in d
    assert "Terms" in d


def test_orias_number_configurable(monkeypatch):
    import importlib

    monkeypatch.setenv("CIF_ORIAS_NUMBER", "12345678")
    try:
        importlib.reload(config)
        assert "12345678" in config.DISCLAIMER
    finally:
        monkeypatch.delenv("CIF_ORIAS_NUMBER")
        importlib.reload(config)


def test_api_returns_disclosure_with_orias(client, ready_user):
    r = client.post("/api/recommendations", headers=ready_user)
    assert config.CIF_ORIAS_NUMBER in r.json()["disclaimer"]


def test_no_denial_of_advice_anywhere():
    root = pathlib.Path(__file__).resolve().parents[2]
    for base in (root / "backend", root / "frontend" / "src"):
        for f in base.rglob("*"):
            if f.is_file() and f.suffix in {".py", ".js", ".jsx"} \
                    and ".venv" not in f.parts and "node_modules" not in f.parts:
                assert ("not financial " + "advice") not in f.read_text(errors="ignore").lower(), f
