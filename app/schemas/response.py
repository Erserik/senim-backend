from datetime import datetime

from pydantic import BaseModel, Field


class CreateResponseRequest(BaseModel):
    price: int = Field(..., gt=0, le=100_000_000)
    message: str | None = Field(None, max_length=500)
    availability: str | None = Field(None, pattern="^(today|tomorrow|this_week|discuss)$")


class UpdateResponseRequest(BaseModel):
    price: int | None = None
    message: str | None = None
    availability: str | None = None


class ResponseOut(BaseModel):
    id: int
    order_id: int
    master_id: int
    price: int
    message: str | None = None
    availability: str | None = None
    status: str
    created_at: datetime
    order_title: str | None = None
    order_category_slug: str | None = None
    order_category_label_ru: str | None = None
    order_category_label_kz: str | None = None
    order_district_label_ru: str | None = None
    order_budget_from: int | None = None
    order_budget_to: int | None = None
    order_is_negotiable: bool = False
    client_name: str | None = None
    client_initials: str | None = None


class ResponseListResponse(BaseModel):
    responses: list[ResponseOut]
    total: int
