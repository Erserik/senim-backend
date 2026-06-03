from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat, Message
from app.models.master_profile import MasterProfile
from app.models.order import Order
from app.models.response import Response
from app.models.review import Review
from app.models.transaction import Transaction
from app.models.user import User
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.profile import ReviewItem
from app.schemas.review import CreateReviewRequest, SendTipRequest, SendTipResponse

router = APIRouter(prefix="/reviews", tags=["reviews"])


async def _recompute_master_stats(master_id: int, db: AsyncSession) -> None:
    mp = (await db.execute(
        select(MasterProfile).where(MasterProfile.user_id == master_id)
    )).scalar_one_or_none()
    if not mp:
        return
    ratings = (await db.execute(
        select(Review.rating).where(
            and_(Review.target_id == master_id, Review.direction == "client_to_master")
        )
    )).scalars().all()
    mp.review_count = len(list(ratings))
    mp.rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
    mp.recompute_tier()


async def _recompute_client_stats(client_id: int, db: AsyncSession) -> None:
    client = (await db.execute(select(User).where(User.id == client_id))).scalar_one_or_none()
    if not client:
        return
    ratings = (await db.execute(
        select(Review.rating).where(
            and_(Review.target_id == client_id, Review.direction == "master_to_client")
        )
    )).scalars().all()
    client.client_review_count = len(list(ratings))
    client.client_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0


@router.post("", response_model=ReviewItem, status_code=status.HTTP_201_CREATED)
async def create_review(
    req: CreateReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = (await db.execute(select(Order).where(Order.id == req.order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order not completed yet")

    accepted = (await db.execute(
        select(Response).where(
            and_(Response.order_id == order.id, Response.status == "accepted")
        )
    )).scalar_one_or_none()
    if not accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No accepted response on this order")

    if user.id == order.client_id:
        direction = "client_to_master"
        target_id = accepted.master_id
    elif user.id == accepted.master_id:
        direction = "master_to_client"
        target_id = order.client_id
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")

    existing = (await db.execute(
        select(Review).where(
            and_(
                Review.order_id == order.id,
                Review.reviewer_id == user.id,
                Review.direction == direction,
            )
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already reviewed")

    review = Review(
        order_id=order.id,
        reviewer_id=user.id,
        target_id=target_id,
        direction=direction,
        rating=req.rating,
        text=req.text,
        tip_amount=req.tip_amount if direction == "client_to_master" else 0,
    )
    db.add(review)
    await db.flush()

    if direction == "client_to_master":
        # Commission deduction + tip credit + order_count bump
        mp = (await db.execute(
            select(MasterProfile).where(MasterProfile.user_id == target_id)
        )).scalar_one_or_none()
        if mp:
            commission = int(accepted.price * mp.commission_percent / 100)
            mp.order_count += 1

            if commission > 0:
                mp.balance -= commission
                db.add(Transaction(
                    user_id=target_id,
                    order_id=order.id,
                    type="commission",
                    amount=-commission,
                    balance_after=mp.balance,
                    description=f"Комиссия {mp.commission_percent}% по заказу #{order.id}",
                ))
            if req.tip_amount > 0:
                mp.balance += req.tip_amount
                db.add(Transaction(
                    user_id=target_id,
                    order_id=order.id,
                    type="tip_received",
                    amount=req.tip_amount,
                    balance_after=mp.balance,
                    description=f"Чаевые по заказу #{order.id}",
                ))
            await _recompute_master_stats(target_id, db)
        user.client_order_count += 1
    else:
        await _recompute_client_stats(target_id, db)

    await db.flush()

    reviewer = user
    return ReviewItem(
        id=review.id,
        reviewer_name=reviewer.full_name or "Аноним",
        reviewer_initials=reviewer.initials,
        reviewer_photo=reviewer.photo_url,
        rating=review.rating,
        text=review.text,
        tip_amount=review.tip_amount,
        direction=review.direction,
        created_at=review.created_at,
    )


@router.post("/tip", response_model=SendTipResponse, status_code=status.HTTP_201_CREATED)
async def send_tip(
    req: SendTipRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = (await db.execute(select(Order).where(Order.id == req.order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only client can tip")
    if order.status not in ("in_progress", "completed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order not in progress/completed")

    accepted = (await db.execute(
        select(Response).where(
            and_(Response.order_id == order.id, Response.status == "accepted")
        )
    )).scalar_one_or_none()
    if not accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No master selected")

    mp = (await db.execute(
        select(MasterProfile).where(MasterProfile.user_id == accepted.master_id)
    )).scalar_one_or_none()
    if not mp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master profile not found")

    mp.balance = (mp.balance or 0) + req.amount
    db.add(Transaction(
        user_id=accepted.master_id,
        order_id=order.id,
        type="tip_received",
        amount=req.amount,
        balance_after=mp.balance,
        description=f"Чаевые по заказу #{order.id}",
    ))

    chat = (await db.execute(select(Chat).where(Chat.order_id == order.id))).scalar_one_or_none()
    if chat:
        db.add(Message(
            chat_id=chat.id,
            sender_id=None,
            type="system",
            system_kind="tip_sent",
            text=f"Клиент отправил чаевые: {req.amount:,} тг".replace(",", " "),
        ))

    await db.flush()
    return SendTipResponse(ok=True, master_balance=mp.balance)
