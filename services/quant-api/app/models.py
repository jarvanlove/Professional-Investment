from datetime import date

from sqlalchemy import Float, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Fund(Base):
    __tablename__ = "funds"
    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    bucket: Mapped[str] = mapped_column(String(16))
    role: Mapped[str] = mapped_column(String(16))
    cap: Mapped[float] = mapped_column(Float)
    proxy_code: Mapped[str | None] = mapped_column(String(8), nullable=True)


class NavHistory(Base):
    __tablename__ = "nav_history"
    __table_args__ = (UniqueConstraint("fund_code", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fund_code: Mapped[str] = mapped_column(String(8), index=True)
    date: Mapped[date]
    nav: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(8), default="auto")


class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date]
    fund_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    direction: Mapped[str] = mapped_column(String(8))  # buy/sell/deposit/withdraw
    amount: Mapped[float] = mapped_column(Float)
    shares: Mapped[float | None] = mapped_column(Float, nullable=True)
    nav: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fee_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class WeeklySignal(Base):
    __tablename__ = "weekly_signals"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    as_of: Mapped[date]
    report_json: Mapped[str] = mapped_column(Text)
    total_value: Mapped[float] = mapped_column(Float)
    net_contributed: Mapped[float] = mapped_column(Float)
