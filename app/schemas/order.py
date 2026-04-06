from datetime import datetime

from pydantic import BaseModel, Field


class OrderCreateRequest(BaseModel):
    category_slug: str
    category_label: str
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    photos: list[str] = Field(default_factory=list)
    district: str | None = None
    address: str | None = None
    date_option: str | None = None
    time_option: str | None = None
    budget_from: int | None = None
    budget_to: int | None = None


class OrderResponse(BaseModel):
    id: int
    client_id: int
    category_slug: str
    category_label: str
    title: str
    description: str | None
    photos: list[str]
    district: str | None
    address: str | None
    date_option: str | None
    time_option: str | None
    budget_from: int | None
    budget_to: int | None
    budget_display: str
    status: str
    response_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int


class OrderDetailResponse(OrderResponse):
    client_name: str | None = None
    client_initials: str | None = None
    responses_list: list["ResponseInOrder"] = Field(default_factory=list)


class ResponseInOrder(BaseModel):
    id: int
    master_id: int
    master_name: str
    master_initials: str
    master_rating: float
    master_review_count: int
    price: int
    description: str | None
    available_when: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
