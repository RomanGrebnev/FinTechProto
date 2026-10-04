import logging
import os
import secrets

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wealthpilot.db")
APP_ENV = os.getenv("APP_ENV", "")
MIN_JWT_SECRET_BYTES = 32


def resolve_jwt_secret(env=os.environ) -> str:
    """Return the JWT signing secret. No default: refuse to start without a strong one, unless APP_ENV=dev."""
    secret = env.get("JWT_SECRET", "")
    if len(secret.encode()) >= MIN_JWT_SECRET_BYTES:
        return secret
    if env.get("APP_ENV") == "dev":
        logging.getLogger(__name__).warning(
            "JWT_SECRET is unset or too short; using a random per-process secret (APP_ENV=dev). "
            "Sessions will not survive a restart."
        )
        return secrets.token_urlsafe(48)
    raise RuntimeError(
        f"JWT_SECRET must be set to at least {MIN_JWT_SECRET_BYTES} bytes "
        "(set APP_ENV=dev only for local development)."
    )


JWT_SECRET = resolve_jwt_secret()
JWT_EXPIRE_HOURS = 24 * 7
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL") or "mistral-large-latest"
BASE_CURRENCY = "EUR"

# Fictional demo value; set the real ORIAS number in production.
CIF_ORIAS_NUMBER = os.getenv("CIF_ORIAS_NUMBER", "00000000")

DISCLAIMER = (
    "Wealthpilot SAS is a conseiller en investissements financiers (CIF) registered with ORIAS under no. "
    f"{CIF_ORIAS_NUMBER}. This is non-independent investment advice, based on the information you provided "
    "in your profile and portfolio. See our Terms of Service (Terms, section 2) for details."
)
