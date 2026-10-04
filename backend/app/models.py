from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    profile: Mapped["RiskProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="Holding.id"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(cascade="all, delete-orphan")


class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    age: Mapped[int] = mapped_column(Integer)
    annual_income: Mapped[float] = mapped_column(Float)
    savings_goal: Mapped[str] = mapped_column(String(64))
    monthly_investment: Mapped[float] = mapped_column(Float)
    risk_tolerance: Mapped[int] = mapped_column(Integer)  # 1-5
    horizon_years: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="profile")


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[float] = mapped_column(Float)
    avg_buy_price: Mapped[float] = mapped_column(Float)

    user: Mapped[User] = relationship(back_populates="holdings")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(16))  # "mistral" | "demo"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
