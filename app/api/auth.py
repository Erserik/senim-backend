from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_sms_code,
    get_current_user,
    peek_sms_code,
    store_sms_code,
    verify_sms_code,
)
from app.models.master_profile import MasterProfile
from app.models.user import User
from app.schemas.auth import (
    ChangePhoneRequest,
    MasterProfilePublic,
    ProfileSetupRequest,
    RoleSetupRequest,
    SendSmsRequest,
    SendSmsResponse,
    UserResponse,
    VerifySmsRequest,
    VerifySmsResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def user_to_response(user: User) -> UserResponse:
    mp_public = None
    if user.master_profile:
        mp = user.master_profile
        mp_public = MasterProfilePublic(
            specializations=mp.specializations or [],
            service_lat=mp.service_lat,
            service_lng=mp.service_lng,
            service_radius_km=mp.service_radius_km,
            tier=mp.tier,
            commission_percent=mp.commission_percent,
            rating=mp.rating or 0.0,
            review_count=mp.review_count or 0,
            order_count=mp.order_count or 0,
            onboarding_complete=mp.onboarding_complete,
            iin_verified=mp.iin_verified,
            balance=mp.balance or 0,
        )
    return UserResponse(
        id=user.id,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        initials=user.initials,
        city_slug=user.city_slug,
        photo_url=user.photo_url,
        role=user.role,
        language=user.language or "ru",
        phone_visible_after_deal=user.phone_visible_after_deal,
        online_status_visible=user.online_status_visible,
        client_rating=user.client_rating or 0.0,
        client_review_count=user.client_review_count or 0,
        client_order_count=user.client_order_count or 0,
        master_profile=mp_public,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


@router.post("/send-sms", response_model=SendSmsResponse)
async def send_sms(req: SendSmsRequest):
    """Send SMS verification code. In dev, the code is returned to display in the UI."""
    code = generate_sms_code()
    store_sms_code(req.phone, code)
    # Dev mode: expose code so the UI can display it.
    return SendSmsResponse(message="SMS sent (dev mode)", dev_code=code)


@router.post("/verify-sms", response_model=VerifySmsResponse)
async def verify_sms(req: VerifySmsRequest, db: AsyncSession = Depends(get_db)):
    if not verify_sms_code(req.phone, req.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или просроченный код",
        )

    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        user = User(phone=req.phone)
        db.add(user)
        await db.flush()

    token = create_access_token(user.id)
    return VerifySmsResponse(access_token=token, is_new_user=is_new)


@router.get("/sms-code/{phone}")
async def peek_code(phone: str):
    """Dev helper: peek at current SMS code without consuming it."""
    return {"phone": phone, "code": peek_sms_code(phone)}


@router.post("/profile", response_model=UserResponse)
async def setup_profile(
    req: ProfileSetupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.first_name = req.first_name
    user.last_name = req.last_name
    user.city_slug = req.city_slug
    if req.photo_url:
        user.photo_url = req.photo_url
    await db.flush()
    return user_to_response(user)


@router.post("/role", response_model=UserResponse)
async def set_role(
    req: RoleSetupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.role = req.role
    if req.role == "master" and user.master_profile is None:
        db.add(MasterProfile(user_id=user.id))
    await db.flush()
    await db.refresh(user)
    return user_to_response(user)


@router.post("/change-phone", response_model=UserResponse)
async def change_phone(
    req: ChangePhoneRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_sms_code(req.phone, req.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или просроченный код",
        )
    existing = await db.execute(select(User).where(User.phone == req.phone))
    owner = existing.scalar_one_or_none()
    if owner is not None and owner.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот номер уже используется",
        )
    user.phone = req.phone
    await db.flush()
    return user_to_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Touch last-seen
    user.last_seen_at = datetime.now(timezone.utc)
    await db.flush()
    return user_to_response(user)
