"""Creates the demo user (idempotent). Run: python seed.py"""

from sqlalchemy import select

from app.auth import hash_password
from app.db import Base, SessionLocal, engine
from app.models import Holding, RiskProfile, User

DEMO_EMAIL = "demo@wealthpilot.fr"
DEMO_PASSWORD = "demo1234"

HOLDINGS = [
    # ticker, quantity, average buy price (in the instrument's currency)
    ("MC.PA", 4, 520.00),     # LVMH
    ("AIR.PA", 15, 150.00),   # Airbus
    ("TTE.PA", 40, 60.00),    # TotalEnergies
    ("CW8.PA", 6, 520.00),    # Amundi MSCI World ETF
    ("AAPL", 10, 210.00),     # Apple (USD)
]


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == DEMO_EMAIL)):
            print(f"Demo user already exists: {DEMO_EMAIL}")
            return
        user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
        user.profile = RiskProfile(
            age=34, annual_income=52000, savings_goal="wealth_growth",
            monthly_investment=400, risk_tolerance=3, horizon_years=15,
        )
        user.holdings = [Holding(ticker=t, quantity=q, avg_buy_price=p) for t, q, p in HOLDINGS]
        db.add(user)
        db.commit()
        print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
