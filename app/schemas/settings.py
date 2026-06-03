from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    language: str = "ru"
    phone_visible_after_deal: bool = True
    online_status_visible: bool = True


class UpdateSettingsRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    city_slug: str | None = None
    photo_url: str | None = None
    language: str | None = Field(None, pattern="^(ru|kz)$")
    phone_visible_after_deal: bool | None = None
    online_status_visible: bool | None = None


class DeleteAccountResponse(BaseModel):
    message: str = "Account deactivated"
