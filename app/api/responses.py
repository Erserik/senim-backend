from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
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

router = APIRouter(prefix="/responses", tags=["responses"])


def _response_to_out(resp: Response, order: Order | None = None) -> ResponseOut:
    return ResponseOut(
        id=resp.id,
        order_id=resp.order_id,
        master_id=resp.master_id,
        price=resp.price,
        description=resp.description,
        available_when=resp.available_when,
        status=resp.status,
        created_at=resp.created_at,
        order_title=order.title if order else None,
        order_category_slug=order.category_slug if order else None,
        order_category_label=order.category_label if order else None,
    )


@router.post("/orders/{order_id}", response_model=ResponseOut, status_code=status.HTTP_201_CREATED)
async def create_response(
    order_id: int,
    req: CreateResponseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a response (bid) to an order (master only)."""
    if user.role != "master":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only masters can respond")

    # Check order exists and is active
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is not active")

    # Check if already responded
    existing = await db.execute(
        select(Response).where(Response.order_id == order_id, Response.master_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already responded to this order")

    response = Response(
        order_id=order_id,
        master_id=user.id,
        price=req.price,
        description=req.description,
        available_when=req.available_when,
    )
    db.add(response)

    # Increment order response count
    order.response_count += 1
    await db.flush()

    return _response_to_out(response, order)


@router.get("/my", response_model=ResponseListResponse)
async def list_my_responses(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List responses submitted by the current master."""
    query = (
        select(Response)
        .options(selectinload(Response.order))
        .where(Response.master_id == user.id)
        .order_by(Response.created_at.desc())
    )

    if status_filter:
        query = query.where(Response.status == status_filter)

    count_q = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    responses = result.scalars().all()

    return ResponseListResponse(
        responses=[_response_to_out(r, r.order) for r in responses],
        total=total,
    )


@router.put("/{response_id}", response_model=ResponseOut)
async def update_response(
    response_id: int,
    req: UpdateResponseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a response (master only, own responses, status=waiting)."""
    result = await db.execute(
        select(Response).options(selectinload(Response.order)).where(Response.id == response_id)
    )
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    if resp.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your response")
    if resp.status != "waiting":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only edit waiting responses")

    if req.price is not None:
        resp.price = req.price
    if req.description is not None:
        resp.description = req.description
    if req.available_when is not None:
        resp.available_when = req.available_when

    await db.flush()
    return _response_to_out(resp, resp.order)


@router.delete("/{response_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_response(
    response_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel/delete a response (master only, own responses, status=waiting)."""
    result = await db.execute(select(Response).where(Response.id == response_id))
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    if resp.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your response")
    if resp.status != "waiting":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only cancel waiting responses")

    # Decrement order response count
    order_result = await db.execute(select(Order).where(Order.id == resp.order_id))
    order = order_result.scalar_one_or_none()
    if order and order.response_count > 0:
        order.response_count -= 1

    await db.delete(resp)
    await db.flush()


@router.post("/{response_id}/accept", response_model=ResponseOut)
async def accept_response(
    response_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a master's response (client only, own order)."""
    result = await db.execute(
        select(Response).options(selectinload(Response.order)).where(Response.id == response_id)
    )
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    order = resp.order
    if order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    if resp.status != "waiting":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Response is not waiting")

    # Accept this response, decline others
    resp.status = "accepted"
    order.status = "in_progress"

    other_responses_result = await db.execute(
        select(Response).where(
            Response.order_id == order.id,
            Response.id != resp.id,
            Response.status == "waiting",
        )
    )
    for other in other_responses_result.scalars().all():
        other.status = "declined"

    # Create chat between client and master
    chat = Chat(
        order_id=order.id,
        client_id=order.client_id,
        master_id=resp.master_id,
    )
    db.add(chat)
    await db.flush()

    # Add system message
    system_msg = Message(
        chat_id=chat.id,
        sender_id=None,
        type="system",
        content="Клиент принял ваш отклик",
    )
    db.add(system_msg)
    await db.flush()

    return _response_to_out(resp, order)
