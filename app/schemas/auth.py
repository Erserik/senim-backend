from datetime import datetime
from pydantic import BaseModel, Field


class SendSmsRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20, examples=["+77771234567"])


class SendSmsResponse(BaseModel):
    message: str = "SMS sent"
    dev_code: str | None = None  # shown in dev — displayed in UI


class VerifySmsRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=4)


class VerifySmsResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool


class ChangePhoneRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=4)


class ProfileSetupRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    city_slug: str = Field(..., min_length=1, max_length=50)
    photo_url: str | None = None


class RoleSetupRequest(BaseModel):
    role: str = Field(..., pattern="^(client|master)$")


class MasterProfilePublic(BaseModel):
    specializations: list[str] = []
    service_lat: float | None = None
    service_lng: float | None = None
    service_radius_km: float | None = None
    tier: str = "new"
    commission_percent: int = 10
    rating: float = 0.0
    review_count: int = 0
    order_count: int = 0
    onboarding_complete: bool = False
    iin_verified: bool = False
    balance: int = 0


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=25, examples=["+77001234567"])


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool


class UserResponse(BaseModel):
    id: int
    phone: str
    first_name: str | None
    last_name: str | None
    full_name: str
    initials: str
    city_slug: str | None
    photo_url: str | None
    role: str | None
    language: str = "ru"
    phone_visible_after_deal: bool = True
    online_status_visible: bool = True
    client_rating: float = 0.0
    client_review_count: int = 0
    client_order_count: int = 0
    master_profile: MasterProfilePublic | None = None
    is_admin: bool = False
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
