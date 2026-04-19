from datetime import datetime

from pydantic import BaseModel


class PriceItem(BaseModel):
    category_slug: str
    price_from: int | None = None
    price_to: int | None = None


class ReviewItem(BaseModel):
    id: int | None = None
    reviewer_name: str
    reviewer_initials: str
    reviewer_photo: str | None = None
    rating: int
    text: str | None = None
    tip_amount: int = 0
    direction: str = "client_to_master"
    created_at: datetime | None = None


class MasterProfileResponse(BaseModel):
    user_id: int
    name: str
    initials: str
    photo_url: str | None = None
    phone: str | None = None
    city_slug: str | None = None
    member_since: str | None = None
    bio: str | None = None
    experience: str | None = None
    tier: str = "new"
    commission_percent: int = 10
    rating: float = 0.0
    review_count: int = 0
    order_count: int = 0
    response_time_minutes: int = 0
    specializations: list[str] = []
    service_lat: float | None = None
    service_lng: float | None = None
    service_radius_km: float | None = None
    portfolio: list[str] = []
    prices: list[PriceItem] = []
    recent_reviews: list[ReviewItem] = []
    iin_verified: bool = False


class ClientProfileResponse(BaseModel):
    user_id: int
    name: str
    initials: str
    photo_url: str | None = None
    city_slug: str | None = None
    member_since: str | None = None
    client_rating: float = 0.0
    client_review_count: int = 0
    client_order_count: int = 0
    recent_reviews: list[ReviewItem] = []


class TopMasterItem(BaseModel):
    user_id: int
    name: str
    initials: str
    photo_url: str | None = None
    tier: str = "new"
    rating: float = 0.0
    review_count: int = 0
    specializations: list[str] = []


class TopMastersResponse(BaseModel):
    masters: list[TopMasterItem]


class RecentReviewsResponse(BaseModel):
    reviews: list[ReviewItem]
