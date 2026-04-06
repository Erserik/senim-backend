from pydantic import BaseModel


class CategoryOut(BaseModel):
    id: int
    slug: str
    label: str
    icon: str
    color: str

    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    categories: list[CategoryOut]


class DistrictOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class DistrictListResponse(BaseModel):
    districts: list[DistrictOut]
