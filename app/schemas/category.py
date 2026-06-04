from pydantic import BaseModel


class SubcategoryOut(BaseModel):
    id: int
    slug: str
    label_ru: str
    label_kz: str
    is_other: bool = False

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: int
    slug: str
    label_ru: str
    label_kz: str
    icon: str
    color: str
    subcategories: list[SubcategoryOut] = []

    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    categories: list[CategoryOut]


class CategoryGroupOut(BaseModel):
    slug: str
    label_ru: str
    label_kz: str
    icon: str
    color: str
    categories: list[CategoryOut] = []


class CategoryGroupsResponse(BaseModel):
    groups: list[CategoryGroupOut]


class DistrictOut(BaseModel):
    id: int
    slug: str
    name_ru: str
    name_kz: str

    model_config = {"from_attributes": True}


class CityOut(BaseModel):
    id: int
    slug: str
    name_ru: str
    name_kz: str
    latitude: float | None = None
    longitude: float | None = None
    districts: list[DistrictOut] = []

    model_config = {"from_attributes": True}


class CityListResponse(BaseModel):
    cities: list[CityOut]


class SearchHit(BaseModel):
    category_slug: str
    category_label_ru: str
    category_label_kz: str
    subcategory_slug: str
    subcategory_label_ru: str
    subcategory_label_kz: str
    matched_keyword: str | None = None


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]
