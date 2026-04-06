from pydantic import BaseModel


class PriceItem(BaseModel):
    category: str
    range: str


class ReviewItem(BaseModel):
    name: str
    rating: int
    text: str | None
    time: str


class MasterProfileResponse(BaseModel):
    user_id: int
    name: str
    initials: str
    rating: float
    reviews: int
    orders: int
    experience: str | None
    response_time: int
    about: str | None
    specializations: list[str]
    portfolio: list[str]
    prices: list[PriceItem]
    districts: list[str]
    recent_reviews: list[ReviewItem] = []
    member_since: str | None = None


class TopMasterItem(BaseModel):
    user_id: int
    name: str
    initials: str
    rating: float
    reviews: int


class TopMastersResponse(BaseModel):
    masters: list[TopMasterItem]


class RecentReviewsResponse(BaseModel):
    reviews: list[ReviewItem]
