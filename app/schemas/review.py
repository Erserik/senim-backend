from pydantic import BaseModel, Field


class CreateReviewRequest(BaseModel):
    order_id: int
    rating: int = Field(..., ge=1, le=5)
    text: str | None = None
    tip_amount: int = Field(0, ge=0)


class SendTipRequest(BaseModel):
    order_id: int
    amount: int = Field(..., gt=0, le=500_000)


class SendTipResponse(BaseModel):
    ok: bool = True
    master_balance: int
