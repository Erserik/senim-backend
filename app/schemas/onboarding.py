from pydantic import BaseModel, Field


class SpecializationsRequest(BaseModel):
    specializations: list[str] = Field(..., min_length=1)


class ExperienceRequest(BaseModel):
    experience: str = Field(..., pattern="^(beginner|mid|expert)$")
    bio: str = Field("", max_length=500)


class PortfolioRequest(BaseModel):
    portfolio: list[str] = Field(default_factory=list)  # list of image URLs


class DistrictsRequest(BaseModel):
    districts: list[str] = Field(..., min_length=1)


class PriceRange(BaseModel):
    from_price: int = Field(..., alias="from", ge=0)
    to_price: int = Field(..., alias="to", ge=0)

    model_config = {"populate_by_name": True}


class PricesRequest(BaseModel):
    prices: dict[str, PriceRange]  # category_slug -> {from, to}


class OnboardingStatusResponse(BaseModel):
    step: str  # current step
    complete: bool
