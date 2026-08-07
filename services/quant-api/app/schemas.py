from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

REASON_CODES = {"B1", "B2", "B3", "B4", "S1", "S2", "S3", "S4", "P1", "P2", "N0"}


class TradeIn(BaseModel):
    date: date
    direction: Literal["buy", "sell", "deposit", "withdraw"]
    fund_code: str | None = None
    amount: float = Field(gt=0)
    shares: float | None = None
    nav: float | None = None
    reason_code: str | None = None
    fee_estimate: float | None = None
    note: str | None = None

    @model_validator(mode="after")
    def check_fields(self):
        if self.direction in ("buy", "sell"):
            if not self.fund_code or self.shares is None or self.nav is None:
                raise ValueError("buy/sell 必须提供 fund_code、shares、nav")
            if self.reason_code is not None and self.reason_code not in REASON_CODES:
                raise ValueError(f"非法理由代码: {self.reason_code}")
        else:
            if self.fund_code is not None:
                raise ValueError("deposit/withdraw 不应带 fund_code")
        return self


class TradeOut(TradeIn):
    id: int

    model_config = {"from_attributes": True}


class TradePage(BaseModel):
    items: list[TradeOut]
    total: int
    page: int
    page_size: int


class DcaPlanIn(BaseModel):
    fund_code: str
    frequency: Literal["weekly", "monthly"]
    amount: float = Field(gt=0)
    day_of_week: int | None = Field(default=None, ge=0, le=4)
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    active: bool = True
    note: str | None = None

    @model_validator(mode="after")
    def check_schedule(self):
        if self.frequency == "weekly" and self.day_of_week is None:
            raise ValueError("周定投必须指定 day_of_week（0-4）")
        if self.frequency == "monthly" and self.day_of_month is None:
            raise ValueError("月定投必须指定 day_of_month（1-28）")
        if self.frequency == "weekly" and self.day_of_month is not None:
            raise ValueError("周定投不应指定 day_of_month")
        if self.frequency == "monthly" and self.day_of_week is not None:
            raise ValueError("月定投不应指定 day_of_week")
        return self


class DcaPlanOut(DcaPlanIn):
    id: int

    model_config = {"from_attributes": True}
