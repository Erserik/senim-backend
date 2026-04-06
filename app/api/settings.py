from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.settings import DeleteAccountResponse, SettingsResponse, UpdateSettingsRequest

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(user: User = Depends(get_current_user)):
    """Get user settings (placeholder — real settings would be in a separate table)."""
    return SettingsResponse()


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    req: UpdateSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile fields."""
    if req.first_name is not None:
        user.first_name = req.first_name
    if req.last_name is not None:
        user.last_name = req.last_name
    if req.city is not None:
        user.city = req.city
    if req.photo_url is not None:
        user.photo_url = req.photo_url
    await db.flush()
    return UserResponse(
        id=user.id,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        city=user.city,
        photo_url=user.photo_url,
        role=user.role,
        initials=user.initials,
    )


@router.delete("/account", response_model=DeleteAccountResponse)
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate user account."""
    user.is_active = False
    await db.flush()
    return DeleteAccountResponse()
