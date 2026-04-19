from datetime import datetime

from pydantic import BaseModel, Field


class OrderCreateRequest(BaseModel):
    category_slug: str
    subcategory_slug: str | None = None
    title: str = Field(..., min_length=3, max_length=200)
    description: str | None = Field(None, max_length=2000)
    photos: list[str] = []
    city_slug: str
    district_slug: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    hide_exact_address: bool = True
    date_option: str | None = None
    preferred_date: str | None = None
    time_from: str | None = None
    time_to: str | None = None
    budget_from: int | None = None
    budget_to: int | None = None
    is_negotiable: bool = False


class ResponsePreview(BaseModel):
    id: int
    master_id: int
    master_name: str
    master_initials: str
    master_photo: str | None = None
    master_rating: float = 0.0
    master_review_count: int = 0
    master_order_count: int = 0
    master_tier: str = "new"
    master_portfolio: list[str] = []
    price: int
    message: str | None = None
    availability: str | None = None
    status: str
    created_at: datetime


class OrderBrief(BaseModel):
    id: int
    client_id: int
    category_slug: str
    category_label_ru: str
    category_label_kz: str
    category_icon: str | None = None
    category_color: str | None = None
    subcategory_slug: str | None = None
    subcategory_label_ru: str | None = None
    subcategory_label_kz: str | None = None
    title: str
    description: str | None = None
    photos: list[str] = []
    city_slug: str
    district_slug: str | None = None
    district_label_ru: str | None = None
    district_label_kz: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    hide_exact_address: bool = True
    date_option: str | None = None
    preferred_date: str | None = None
    time_from: str | None = None
    time_to: str | None = None
    budget_from: int | None = None
    budget_to: int | None = None
    is_negotiable: bool = False
    status: str
    response_count: int = 0
    view_count: int = 0
    selected_response_id: int | None = None
    is_boosted: bool = False
    boosted_until: datetime | None = None
    created_at: datetime
    completed_at: datetime | None = None


class OrderDetail(OrderBrief):
    client_name: str | None = None
    client_initials: str | None = None
    client_photo: str | None = None
    client_rating: float = 0.0
    client_review_count: int = 0
    client_phone: str | None = None
    my_response: ResponsePreview | None = None
    responses: list[ResponsePreview] = []


class OrderListResponse(BaseModel):
    orders: list[OrderBrief]
    total: int
