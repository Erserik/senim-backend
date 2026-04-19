from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.master_profile import MasterProfile
from app.models.review import Review
from app.models.user import User
from app.schemas.profile import (
    ClientProfileResponse,
    MasterProfileResponse,
    PriceItem,
    RecentReviewsResponse,
    ReviewItem,
    TopMasterItem,
    TopMastersResponse,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _member_since(user: User) -> str | None:
    if not user.created_at:
        return None
    months_ru = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
    }
    dt = user.created_at
    return f"С {months_ru.get(dt.month, '')} {dt.year}"


def _review_item(review: Review) -> ReviewItem:
    reviewer = review.reviewer
    return ReviewItem(
        id=review.id,
        reviewer_name=reviewer.full_name if reviewer else "Аноним",
        reviewer_initials=reviewer.initials if reviewer else "??",
        reviewer_photo=reviewer.photo_url if reviewer else None,
        rating=review.rating,
        text=review.text,
        tip_amount=review.tip_amount,
        direction=review.direction,
        created_at=review.created_at,
    )


def _master_profile_response(user: User, mp: MasterProfile, reviews: list[Review]) -> MasterProfileResponse:
    prices = []
    for cat_slug, rng in (mp.prices or {}).items():
        prices.append(PriceItem(
            category_slug=cat_slug,
            price_from=rng.get("from"),
            price_to=rng.get("to"),
        ))
    return MasterProfileResponse(
        user_id=user.id,
        name=user.full_name or "Мастер",
        initials=user.initials,
        photo_url=user.photo_url,
        city_slug=user.city_slug,
        member_since=_member_since(user),
        bio=mp.bio,
        experience=mp.experience,
        tier=mp.tier,
        commission_percent=mp.commission_percent,
        rating=mp.rating or 0.0,
        review_count=mp.review_count or 0,
        order_count=mp.order_count or 0,
        response_time_minutes=mp.response_time_minutes or 0,
        specializations=mp.specializations or [],
        service_lat=mp.service_lat,
        service_lng=mp.service_lng,
        service_radius_km=mp.service_radius_km,
        portfolio=mp.portfolio or [],
        prices=prices,
        recent_reviews=[_review_item(r) for r in reviews],
        iin_verified=mp.iin_verified,
    )


@router.get("/me", response_model=MasterProfileResponse)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "master" or not user.master_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a master")
    reviews = (await db.execute(
        select(Review)
        .options(selectinload(Review.reviewer))
        .where(Review.target_id == user.id, Review.direction == "client_to_master")
        .order_by(Review.created_at.desc())
        .limit(10)
    )).scalars().all()
    return _master_profile_response(user, user.master_profile, list(reviews))


@router.get("/master/{user_id}", response_model=MasterProfileResponse)
async def get_master_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    u = (await db.execute(
        select(User).options(selectinload(User.master_profile)).where(User.id == user_id)
    )).scalar_one_or_none()
    if not u or u.role != "master" or not u.master_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")
    reviews = (await db.execute(
        select(Review)
        .options(selectinload(Review.reviewer))
        .where(Review.target_id == user_id, Review.direction == "client_to_master")
        .order_by(Review.created_at.desc())
        .limit(10)
    )).scalars().all()
    return _master_profile_response(u, u.master_profile, list(reviews))


@router.get("/client/{user_id}", response_model=ClientProfileResponse)
async def get_client_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    reviews = (await db.execute(
        select(Review)
        .options(selectinload(Review.reviewer))
        .where(Review.target_id == user_id, Review.direction == "master_to_client")
        .order_by(Review.created_at.desc())
        .limit(10)
    )).scalars().all()
    return ClientProfileResponse(
        user_id=u.id,
        name=u.full_name or "Клиент",
        initials=u.initials,
        photo_url=u.photo_url,
        city_slug=u.city_slug,
        member_since=_member_since(u),
        client_rating=u.client_rating or 0.0,
        client_review_count=u.client_review_count or 0,
        client_order_count=u.client_order_count or 0,
        recent_reviews=[_review_item(r) for r in reviews],
    )


@router.get("/top-masters", response_model=TopMastersResponse)
async def get_top_masters(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MasterProfile)
        .where(MasterProfile.onboarding_complete == True)  # noqa: E712
        .order_by(MasterProfile.rating.desc())
        .limit(10)
    )
    profiles = list(result.scalars().all())

    masters: list[TopMasterItem] = []
    for p in profiles:
        u = (await db.execute(select(User).where(User.id == p.user_id))).scalar_one_or_none()
        if not u:
            continue
        masters.append(TopMasterItem(
            user_id=u.id,
            name=u.full_name or "Мастер",
            initials=u.initials,
            photo_url=u.photo_url,
            tier=p.tier,
            rating=p.rating or 0.0,
            review_count=p.review_count or 0,
            specializations=p.specializations or [],
        ))
    return TopMastersResponse(masters=masters)


@router.get("/recent-reviews", response_model=RecentReviewsResponse)
async def get_recent_reviews(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.reviewer))
        .where(Review.direction == "client_to_master")
        .order_by(Review.created_at.desc())
        .limit(10)
    )
    reviews = result.scalars().all()
    return RecentReviewsResponse(reviews=[_review_item(r) for r in reviews])
