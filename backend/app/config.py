import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wealthpilot.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_EXPIRE_HOURS = 24 * 7
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL") or "mistral-large-latest"
BASE_CURRENCY = "EUR"

DISCLAIMER = (
    "Wealthpilot provides information and educational content only. "
    "This is not financial advice. Always consult a certified investment "
    "advisor before making investment decisions."
)
