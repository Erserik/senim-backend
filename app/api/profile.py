from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.master_profile import MasterProfile
from app.models.review import Review
from app.models.user import User
from app.schemas.profile import (
    MasterProfileResponse,
    PriceItem,
    RecentReviewsResponse,
    ReviewItem,
    TopMasterItem,
    TopMastersResponse,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _build_profile_response(user: User, profile: MasterProfile, reviews: list | None = None) -> MasterProfileResponse:
    # Build prices list
    prices_list = []
    if profile.prices:
        for cat_slug, price_range in profile.prices.items():
            from_p = price_range.get("from", 0)
            to_p = price_range.get("to", 0)
            if from_p and to_p:
                range_str = f"{from_p:,} – {to_p:,} тг".replace(",", " ")
            elif from_p:
                range_str = f"от {from_p:,} тг".replace(",", " ")
            else:
                range_str = "Договорная"
            prices_list.append(PriceItem(category=cat_slug, range=range_str))

    # Experience display
    exp_map = {"beginner": "< 1 года", "mid": "1-3 года", "expert": "> 3 лет"}
    exp_display = exp_map.get(profile.experience or "", profile.experience)

    # Member since
    member_since = None
    if user.created_at:
        months_ru = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
        }
        dt = user.created_at
        member_since = f"На платформе с {months_ru.get(dt.month, '')} {dt.year}"

    # Reviews
    review_items = []
    if reviews:
        for r in reviews:
            client = r.client
            review_items.append(
                ReviewItem(
                    name=client.full_name if client else "Аноним",
                    rating=r.rating,
                    text=r.text,
                    time=r.created_at.strftime("%d.%m.%Y") if r.created_at else "",
                )
            )

    return MasterProfileResponse(
        user_id=user.id,
        name=user.full_name,
        initials=user.initials,
        rating=profile.rating or 0.0,
        reviews=profile.review_count or 0,
        orders=profile.order_count or 0,
        experience=exp_display,
        response_time=profile.response_time_minutes or 0,
        about=profile.bio,
        specializations=profile.specializations or [],
        portfolio=profile.portfolio or [],
        prices=prices_list,
        districts=profile.districts or [],
        recent_reviews=review_items,
        member_since=member_since,
    )


@router.get("/me", response_model=MasterProfileResponse)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current master's profile."""
    if user.role != "master" or not user.master_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a master")

    # Get recent reviews
    reviews_result = await db.execute(
        select(Review)
        .where(Review.master_id == user.id)
        .order_by(Review.created_at.desc())
        .limit(10)
    )
    reviews = reviews_result.scalars().all()

    return _build_profile_response(user, user.master_profile, reviews)


@router.get("/{user_id}", response_model=MasterProfileResponse)
async def get_master_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get any master's public profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user or target_user.role != "master" or not target_user.master_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")

    reviews_result = await db.execute(
        select(Review)
        .where(Review.master_id == user_id)
        .order_by(Review.created_at.desc())
        .limit(10)
    )
    reviews = reviews_result.scalars().all()

    return _build_profile_response(target_user, target_user.master_profile, reviews)


@router.get("/top/masters", response_model=TopMastersResponse)
async def get_top_masters(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get top-rated masters for the client home page."""
    result = await db.execute(
        select(MasterProfile)
        .options()
        .where(MasterProfile.onboarding_complete == True)  # noqa: E712
        .order_by(MasterProfile.rating.desc())
        .limit(10)
    )
    profiles = result.scalars().all()

    masters = []
    for p in profiles:
        user_result = await db.execute(select(User).where(User.id == p.user_id))
        u = user_result.scalar_one_or_none()
        if u:
            masters.append(
                TopMasterItem(
                    user_id=u.id,
                    name=u.full_name,
                    initials=u.initials,
                    rating=p.rating or 0.0,
                    reviews=p.review_count or 0,
                )
            )

    return TopMastersResponse(masters=masters)


@router.get("/reviews/recent", response_model=RecentReviewsResponse)
async def get_recent_reviews(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get recent reviews across the platform."""
    result = await db.execute(
        select(Review).order_by(Review.created_at.desc()).limit(10)
    )
    reviews = result.scalars().all()

    items = []
    for r in reviews:
        client_result = await db.execute(select(User).where(User.id == r.client_id))
        client = client_result.scalar_one_or_none()
        items.append(
            ReviewItem(
                name=client.full_name if client else "Аноним",
                rating=r.rating,
                text=r.text,
                time=r.created_at.strftime("%d.%m.%Y") if r.created_at else "",
            )
        )

    return RecentReviewsResponse(reviews=items)
