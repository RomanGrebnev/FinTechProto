import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import resolve_jwt_secret

BACKEND = Path(__file__).resolve().parents[1]


def test_missing_secret_fails_outside_dev():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        resolve_jwt_secret({})


def test_short_secret_fails():
    with pytest.raises(RuntimeError):
        resolve_jwt_secret({"JWT_SECRET": "short"})


def test_strong_secret_is_used():
    s = "x" * 32
    assert resolve_jwt_secret({"JWT_SECRET": s}) == s


def test_dev_mode_generates_random_secret_without_logging_it(caplog):
    a = resolve_jwt_secret({"APP_ENV": "dev"})
    b = resolve_jwt_secret({"APP_ENV": "dev"})
    assert len(a) >= 32 and a != b
    assert a not in caplog.text and "random per-process" in caplog.text


def test_app_import_exits_without_secret():
    env = {k: v for k, v in os.environ.items() if k not in ("JWT_SECRET", "APP_ENV")}
    env["DATABASE_URL"] = "sqlite://"
    p = subprocess.run([sys.executable, "-c", "import app.main"], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert p.returncode != 0
    assert "JWT_SECRET must be set" in p.stderr
