from datetime import datetime

from pydantic import BaseModel, Field


class CreateResponseRequest(BaseModel):
    price: int = Field(..., gt=0)
    description: str | None = Field(None, max_length=300)
    available_when: str | None = None  # 'Сегодня', 'Завтра', 'На этой неделе'


class UpdateResponseRequest(BaseModel):
    price: int | None = Field(None, gt=0)
    description: str | None = Field(None, max_length=300)
    available_when: str | None = None


class ResponseOut(BaseModel):
    id: int
    order_id: int
    master_id: int
    price: int
    description: str | None
    available_when: str | None
    status: str
    created_at: datetime

    # Enriched fields
    order_title: str | None = None
    order_category_slug: str | None = None
    order_category_label: str | None = None

    model_config = {"from_attributes": True}


class ResponseListResponse(BaseModel):
    responses: list[ResponseOut]
    total: int
