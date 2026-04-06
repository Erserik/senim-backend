from pydantic import BaseModel


class SettingsResponse(BaseModel):
    notifications_enabled: bool = True
    language: str = "ru"
    theme: str = "light"


class UpdateSettingsRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    city: str | None = None
    photo_url: str | None = None


class DeleteAccountResponse(BaseModel):
    message: str = "Account deleted"
