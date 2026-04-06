from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.master_profile import MasterProfile
from app.models.order import Order
from app.models.review import Review
from app.models.user import User
from app.schemas.profile import ReviewItem

from pydantic import BaseModel, Field


class CreateReviewRequest(BaseModel):
    order_id: int
    master_id: int
    rating: int = Field(..., ge=1, le=5)
    text: str | None = None


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewItem, status_code=status.HTTP_201_CREATED)
async def create_review(
    req: CreateReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a review for a completed order (client only)."""
    if user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clients can review")

    # Verify order belongs to client and is completed
    order_result = await db.execute(select(Order).where(Order.id == req.order_id))
    order = order_result.scalar_one_or_none()
    if not order or order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Check no duplicate review
    existing = await db.execute(
        select(Review).where(Review.order_id == req.order_id, Review.client_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already reviewed")

    review = Review(
        order_id=req.order_id,
        client_id=user.id,
        master_id=req.master_id,
        rating=req.rating,
        text=req.text,
    )
    db.add(review)
    await db.flush()

    # Update master profile stats
    mp_result = await db.execute(
        select(MasterProfile).where(MasterProfile.user_id == req.master_id)
    )
    mp = mp_result.scalar_one_or_none()
    if mp:
        mp.review_count += 1
        # Recalculate average rating
        all_reviews = await db.execute(
            select(Review.rating).where(Review.master_id == req.master_id)
        )
        ratings = [r[0] for r in all_reviews.all()]
        mp.rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
        await db.flush()

    return ReviewItem(
        name=user.full_name,
        rating=review.rating,
        text=review.text,
        time=review.created_at.strftime("%d.%m.%Y") if review.created_at else "",
    )
