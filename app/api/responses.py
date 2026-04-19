from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.chat import Chat, Message
from app.models.order import Order
from app.models.response import Response
from app.models.user import User
from app.schemas.response import (
    CreateResponseRequest,
    ResponseListResponse,
    ResponseOut,
    UpdateResponseRequest,
)

router = APIRouter(tags=["responses"])


def _resp_out(r: Response, order: Order | None, client: User | None = None) -> ResponseOut:
    return ResponseOut(
        id=r.id,
        order_id=r.order_id,
        master_id=r.master_id,
        price=r.price,
        message=r.message,
        availability=r.availability,
        status=r.status,
        created_at=r.created_at,
        order_title=order.title if order else None,
        order_category_slug=order.category_slug if order else None,
        order_category_label_ru=order.category_label_ru if order else None,
        order_category_label_kz=order.category_label_kz if order else None,
        order_district_label_ru=order.district_label_ru if order else None,
        order_budget_from=order.budget_from if order else None,
        order_budget_to=order.budget_to if order else None,
        order_is_negotiable=order.is_negotiable if order else False,
        client_name=client.full_name if client else None,
        client_initials=client.initials if client else None,
    )


@router.post("/orders/{order_id}/responses", response_model=ResponseOut, status_code=status.HTTP_201_CREATED)
async def create_response(
    order_id: int,
    req: CreateResponseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "master":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only masters can respond")
    if not user.master_profile or not user.master_profile.onboarding_complete:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete onboarding first")

    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is not active")
    if order.client_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot respond to own order")

    existing = (await db.execute(
        select(Response).where(
            and_(Response.order_id == order_id, Response.master_id == user.id)
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already responded")

    resp = Response(
        order_id=order_id,
        master_id=user.id,
        price=req.price,
        message=req.message,
        availability=req.availability,
        status="pending",
    )
    db.add(resp)
    order.response_count += 1
    await db.flush()
    return _resp_out(resp, order)


@router.get("/orders/{order_id}/responses", response_model=ResponseListResponse)
async def list_order_responses(
    order_id: int,
    sort: str | None = Query(None, pattern="^(default|cheapest|priciest|rating)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")

    result = await db.execute(
        select(Response)
        .options(selectinload(Response.master).selectinload(User.master_profile))
        .where(Response.order_id == order_id)
    )
    rows = list(result.scalars().all())

    if sort == "cheapest":
        rows.sort(key=lambda r: r.price)
    elif sort == "priciest":
        rows.sort(key=lambda r: -r.price)
    elif sort == "rating":
        rows.sort(key=lambda r: -((r.master.master_profile.rating if r.master and r.master.master_profile else 0) or 0))
    else:
        rows.sort(key=lambda r: r.created_at, reverse=True)

    return ResponseListResponse(
        responses=[_resp_out(r, order) for r in rows],
        total=len(rows),
    )


@router.get("/responses/my", response_model=ResponseListResponse)
async def list_my_responses(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Response)
        .options(selectinload(Response.order).selectinload(Order.client))
        .where(Response.master_id == user.id)
        .order_by(Response.created_at.desc())
    )
    if status_filter == "active":
        query = query.where(Response.status.in_(["pending", "viewed"]))
    elif status_filter == "accepted":
        query = query.where(Response.status == "accepted")
    elif status_filter == "archive":
        query = query.where(Response.status.in_(["rejected", "retracted"]))
    elif status_filter:
        query = query.where(Response.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (await db.execute(query.offset(offset).limit(limit))).scalars().all()

    return ResponseListResponse(
        responses=[_resp_out(r, r.order, r.order.client if r.order else None) for r in rows],
        total=total,
    )


@router.put("/responses/{response_id}", response_model=ResponseOut)
async def update_response(
    response_id: int,
    req: UpdateResponseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(
        select(Response).options(selectinload(Response.order)).where(Response.id == response_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    if r.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your response")
    if r.status not in ("pending", "viewed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit")

    if req.price is not None:
        r.price = req.price
    if req.message is not None:
        r.message = req.message
    if req.availability is not None:
        r.availability = req.availability
    await db.flush()
    return _resp_out(r, r.order)


@router.post("/responses/{response_id}/retract", status_code=status.HTTP_204_NO_CONTENT)
async def retract_response(
    response_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(select(Response).where(Response.id == response_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    if r.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your response")
    if r.status not in ("pending", "viewed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot retract")

    r.status = "retracted"
    order = (await db.execute(select(Order).where(Order.id == r.order_id))).scalar_one_or_none()
    if order and order.response_count > 0:
        order.response_count -= 1
    await db.flush()


@router.post("/responses/{response_id}/accept", response_model=ResponseOut)
async def accept_response(
    response_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(
        select(Response).options(selectinload(Response.order)).where(Response.id == response_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    order = r.order
    if order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    if r.status not in ("pending", "viewed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot accept")

    r.status = "accepted"
    order.status = "in_progress"
    order.selected_response_id = r.id

    others = (await db.execute(
        select(Response).where(
            and_(
                Response.order_id == order.id,
                Response.id != r.id,
                Response.status.in_(["pending", "viewed"]),
            )
        )
    )).scalars().all()
    for o in others:
        o.status = "rejected"

    # Create chat
    chat = Chat(
        order_id=order.id,
        client_id=order.client_id,
        master_id=r.master_id,
        response_id=r.id,
    )
    db.add(chat)
    await db.flush()

    db.add(Message(
        chat_id=chat.id,
        sender_id=None,
        type="system",
        system_kind="proposal_accepted",
        text="Клиент принял ваш отклик",
    ))
    await db.flush()

    return _resp_out(r, order)


@router.post("/responses/{response_id}/reject", response_model=ResponseOut)
async def reject_response(
    response_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(
        select(Response).options(selectinload(Response.order)).where(Response.id == response_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    if r.order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")

    r.status = "rejected"
    await db.flush()
    return _resp_out(r, r.order)
