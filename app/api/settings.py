from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import user_to_response
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.settings import DeleteAccountResponse, SettingsResponse, UpdateSettingsRequest

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(user: User = Depends(get_current_user)):
    return SettingsResponse(
        language=user.language or "ru",
        phone_visible_after_deal=user.phone_visible_after_deal,
        online_status_visible=user.online_status_visible,
    )


@router.put("/profile", response_model=UserResponse)
async def update_settings(
    req: UpdateSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.first_name is not None:
        user.first_name = req.first_name
    if req.last_name is not None:
        user.last_name = req.last_name
    if req.city_slug is not None:
        user.city_slug = req.city_slug
    if req.photo_url is not None:
        user.photo_url = req.photo_url
    if req.language is not None:
        user.language = req.language
    if req.phone_visible_after_deal is not None:
        user.phone_visible_after_deal = req.phone_visible_after_deal
    if req.online_status_visible is not None:
        user.online_status_visible = req.online_status_visible
    await db.flush()
    return user_to_response(user)


@router.delete("/account", response_model=DeleteAccountResponse)
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.is_active = False
    await db.flush()
    return DeleteAccountResponse()
