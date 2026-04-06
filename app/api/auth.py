from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_sms_code,
    get_current_user,
    store_sms_code,
    verify_sms_code,
)
from app.models.user import User
from app.schemas.auth import (
    ProfileSetupRequest,
    RoleSetupRequest,
    SendSmsRequest,
    SendSmsResponse,
    VerifySmsRequest,
    VerifySmsResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-sms", response_model=SendSmsResponse)
async def send_sms(req: SendSmsRequest):
    """Send SMS verification code to phone number."""
    code = generate_sms_code()
    store_sms_code(req.phone, code)

    # TODO: integrate real SMS provider (e.g. smsc.kz, mobizon)
    # Code is stored server-side only — never expose it in the response
    return SendSmsResponse(message="SMS sent")


@router.post("/verify-sms", response_model=VerifySmsResponse)
async def verify_sms(req: VerifySmsRequest, db: AsyncSession = Depends(get_db)):
    """Verify SMS code and return access token."""
    if not verify_sms_code(req.phone, req.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code",
        )

    # Find or create user
    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        user = User(phone=req.phone)
        db.add(user)
        await db.flush()

    token = create_access_token(user.id)
    return VerifySmsResponse(access_token=token, is_new_user=is_new)


@router.post("/profile", response_model=UserResponse)
async def setup_profile(
    req: ProfileSetupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set up user profile (name, city, photo)."""
    user.first_name = req.first_name
    user.last_name = req.last_name
    user.city = req.city
    if req.photo_url:
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


@router.post("/role", response_model=UserResponse)
async def set_role(
    req: RoleSetupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set user role (client or master)."""
    user.role = req.role

    # Create master profile if selecting master role
    if req.role == "master" and user.master_profile is None:
        from app.models.master_profile import MasterProfile
        profile = MasterProfile(user_id=user.id)
        db.add(profile)

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


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info."""
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
