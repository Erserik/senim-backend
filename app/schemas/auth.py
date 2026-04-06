from pydantic import BaseModel, Field


class SendSmsRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20, examples=["+77771234567"])


class SendSmsResponse(BaseModel):
    message: str = "SMS sent"


class VerifySmsRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=4)


class VerifySmsResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool


class ProfileSetupRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    city: str = Field(..., min_length=1, max_length=100)
    photo_url: str | None = None


class RoleSetupRequest(BaseModel):
    role: str = Field(..., pattern="^(client|master)$")


class UserResponse(BaseModel):
    id: int
    phone: str
    first_name: str | None
    last_name: str | None
    city: str | None
    photo_url: str | None
    role: str | None
    initials: str

    model_config = {"from_attributes": True}
