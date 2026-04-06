from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.order import Order
from app.models.response import Response
from app.models.user import User
from app.schemas.order import (
    OrderCreateRequest,
    OrderDetailResponse,
    OrderListResponse,
    OrderResponse,
    ResponseInOrder,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        client_id=order.client_id,
        category_slug=order.category_slug,
        category_label=order.category_label,
        title=order.title,
        description=order.description,
        photos=order.photos or [],
        district=order.district,
        address=order.address,
        date_option=order.date_option,
        time_option=order.time_option,
        budget_from=order.budget_from,
        budget_to=order.budget_to,
        budget_display=order.budget_display,
        status=order.status,
        response_count=order.response_count,
        created_at=order.created_at,
    )


@router.get("", response_model=OrderListResponse)
async def list_orders(
    category: str | None = Query(None, description="Filter by category slug"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List orders visible to masters (all active orders)."""
    query = select(Order).order_by(Order.created_at.desc())

    if category:
        query = query.where(Order.category_slug == category)
    if status_filter:
        query = query.where(Order.status == status_filter)
    else:
        query = query.where(Order.status == "active")

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        orders=[_order_to_response(o) for o in orders],
        total=total,
    )


@router.get("/my", response_model=OrderListResponse)
async def list_my_orders(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List orders created by the current client."""
    query = (
        select(Order)
        .where(Order.client_id == user.id)
        .order_by(Order.created_at.desc())
    )

    if status_filter:
        query = query.where(Order.status == status_filter)

    count_q = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        orders=[_order_to_response(o) for o in orders],
        total=total,
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    req: OrderCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new order (client only)."""
    if user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clients can create orders")

    order = Order(
        client_id=user.id,
        category_slug=req.category_slug,
        category_label=req.category_label,
        title=req.title,
        description=req.description,
        photos=req.photos,
        district=req.district,
        address=req.address,
        date_option=req.date_option,
        time_option=req.time_option,
        budget_from=req.budget_from,
        budget_to=req.budget_to,
    )
    db.add(order)
    await db.flush()
    return _order_to_response(order)


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get order details with responses."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.responses).selectinload(Response.master))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Build response list with master info
    responses_list = []
    for resp in order.responses:
        master = resp.master
        mp = master.master_profile if master else None
        responses_list.append(
            ResponseInOrder(
                id=resp.id,
                master_id=resp.master_id,
                master_name=master.full_name if master else "Unknown",
                master_initials=master.initials if master else "??",
                master_rating=mp.rating if mp else 0.0,
                master_review_count=mp.review_count if mp else 0,
                price=resp.price,
                description=resp.description,
                available_when=resp.available_when,
                status=resp.status,
                created_at=resp.created_at,
            )
        )

    client = order.client
    return OrderDetailResponse(
        id=order.id,
        client_id=order.client_id,
        category_slug=order.category_slug,
        category_label=order.category_label,
        title=order.title,
        description=order.description,
        photos=order.photos or [],
        district=order.district,
        address=order.address,
        date_option=order.date_option,
        time_option=order.time_option,
        budget_from=order.budget_from,
        budget_to=order.budget_to,
        budget_display=order.budget_display,
        status=order.status,
        response_count=order.response_count,
        created_at=order.created_at,
        client_name=client.full_name if client else None,
        client_initials=client.initials if client else None,
        responses_list=responses_list,
    )


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an order (client only, own orders)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    if order.status not in ("active",):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel this order")

    order.status = "cancelled"
    await db.flush()
    return _order_to_response(order)
