from datetime import datetime
from pydantic import BaseModel, Field


class BalanceOut(BaseModel):
    balance: int
    tier: str = "new"
    commission_percent: int = 10


class TopupRequest(BaseModel):
    amount: int = Field(..., gt=0, le=10_000_000)


class TransactionOut(BaseModel):
    id: int
    type: str
    amount: int
    balance_after: int
    description: str | None = None
    created_at: datetime


class TransactionListResponse(BaseModel):
    transactions: list[TransactionOut]
