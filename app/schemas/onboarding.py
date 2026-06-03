from pydantic import BaseModel, Field


class SpecializationsRequest(BaseModel):
    specializations: list[str] = Field(..., min_length=1, max_length=12)


class ExperienceRequest(BaseModel):
    experience: str = Field(..., pattern="^(lt1|1to5|gt5)$")
    bio: str | None = Field(None, max_length=500)


class PortfolioRequest(BaseModel):
    portfolio: list[str] = []  # list of image URLs


class ServiceAreaRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(..., gt=0, le=200)


class PriceRange(BaseModel):
    from_: int | None = Field(None, alias="from")
    to: int | None = None

    model_config = {"populate_by_name": True}


class PricesRequest(BaseModel):
    prices: dict[str, PriceRange]


class IinRequest(BaseModel):
    iin: str = Field(..., min_length=12, max_length=12, pattern=r"^\d{12}$")


class OnboardingStatusResponse(BaseModel):
    step: str
    complete: bool
    specializations: list[str] = []
    experience: str | None = None
    portfolio: list[str] = []
    service_lat: float | None = None
    service_lng: float | None = None
    service_radius_km: float | None = None
    prices: dict = {}
    bio: str | None = None
    iin_verified: bool = False
