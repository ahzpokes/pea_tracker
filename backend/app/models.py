from datetime import datetime, date, timezone
from sqlalchemy import String, Float, Boolean, DateTime, Date, Integer, ForeignKey, UniqueConstraint, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(primary_key=True)
    isin: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    yahoo_symbol: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    exchange: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_benchmark: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    prices: Mapped[list["DailyPrice"]] = relationship(
        back_populates="instrument",
        cascade="all, delete-orphan"
    )


class DailyPrice(Base):
    __tablename__ = "daily_prices"
    __table_args__ = (
        UniqueConstraint("instrument_id", "price_date", name="uq_instrument_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), index=True
    )
    price_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="yfinance")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    instrument: Mapped["Instrument"] = relationship(back_populates="prices")


class MonthlySignal(Base):
    __tablename__ = "monthly_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_date: Mapped[date] = mapped_column(Date, index=True)
    selected_instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id"), nullable=True
    )
    previous_instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id"), nullable=True
    )
    signal_type: Mapped[str] = mapped_column(String(50))
    leader_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    second_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_gap: Mapped[float | None] = mapped_column(Float, nullable=True)
    leader_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    leader_sma200: Mapped[float | None] = mapped_column(Float, nullable=True)
    leader_above_sma200: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    threshold_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculation_details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    setting_value: Mapped[str] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class AICommentary(Base):
    __tablename__ = "ai_commentaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_signal_id: Mapped[int | None] = mapped_column(
        ForeignKey("monthly_signals.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="local")
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    decision_explained: Mapped[str] = mapped_column(Text)
    risk_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))