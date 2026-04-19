from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.chat import Chat
from app.models.master_profile import MasterProfile
from app.models.order import Order
from app.models.response import Response
from app.models.review import Review
from app.models.transaction import Transaction
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


class AdminStats(BaseModel):
    active_orders: int
    total_orders: int
    total_users: int
    total_masters: int
    total_clients: int
    active_chats: int
    total_revenue: int
    new_registrations_24h: int


class AdminUserItem(BaseModel):
    id: int
    phone: str
    full_name: str
    role: str | None
    is_admin: bool
    is_banned: bool
    created_at: datetime
    tier: str | None = None
    rating: float = 0.0


class AdminOrderItem(BaseModel):
    id: int
    title: str
    status: str
    client_name: str | None
    category_label_ru: str
    budget_from: int | None
    budget_to: int | None
    is_negotiable: bool
    response_count: int
    created_at: datetime


class AdminChatItem(BaseModel):
    id: int
    order_id: int
    order_title: str | None
    client_name: str
    master_name: str
    message_count: int
    is_confirmed: bool


@router.get("/stats", response_model=AdminStats)
async def stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    total_masters = (await db.execute(select(func.count()).select_from(User).where(User.role == "master"))).scalar() or 0
    total_clients = (await db.execute(select(func.count()).select_from(User).where(User.role == "client"))).scalar() or 0
    active_orders = (await db.execute(select(func.count()).select_from(Order).where(Order.status == "active"))).scalar() or 0
    total_orders = (await db.execute(select(func.count()).select_from(Order))).scalar() or 0
    active_chats = (await db.execute(select(func.count()).select_from(Chat))).scalar() or 0
    revenue = (await db.execute(
        select(func.coalesce(func.sum(-Transaction.amount), 0)).where(Transaction.type == "commission")
    )).scalar() or 0
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    new_regs = (await db.execute(select(func.count()).select_from(User).where(User.created_at >= since))).scalar() or 0
    return AdminStats(
        active_orders=active_orders,
        total_orders=total_orders,
        total_users=total_users,
        total_masters=total_masters,
        total_clients=total_clients,
        active_chats=active_chats,
        total_revenue=int(revenue),
        new_registrations_24h=new_regs,
    )


@router.get("/users", response_model=list[AdminUserItem])
async def list_users(
    q: str | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(User)
        .options(selectinload(User.master_profile))
        .order_by(User.created_at.desc())
        .limit(200)
    )
    if q:
        like = f"%{q}%"
        query = query.where(
            (User.phone.like(like)) | (User.first_name.like(like)) | (User.last_name.like(like))
        )
    users = (await db.execute(query)).scalars().all()
    return [
        AdminUserItem(
            id=u.id,
            phone=u.phone,
            full_name=u.full_name or "—",
            role=u.role,
            is_admin=u.is_admin,
            is_banned=u.is_banned,
            created_at=u.created_at,
            tier=u.master_profile.tier if u.master_profile else None,
            rating=(u.master_profile.rating if u.master_profile else 0.0) or 0.0,
        )
        for u in users
    ]


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if u.is_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot ban admin")
    u.is_banned = not u.is_banned
    await db.flush()
    return {"ok": True, "is_banned": u.is_banned}


@router.get("/orders", response_model=list[AdminOrderItem])
async def list_admin_orders(
    status_filter: str | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Order)
        .options(selectinload(Order.client))
        .order_by(Order.created_at.desc())
        .limit(200)
    )
    if status_filter:
        query = query.where(Order.status == status_filter)
    orders = (await db.execute(query)).scalars().all()
    return [
        AdminOrderItem(
            id=o.id,
            title=o.title,
            status=o.status,
            client_name=o.client.full_name if o.client else None,
            category_label_ru=o.category_label_ru,
            budget_from=o.budget_from,
            budget_to=o.budget_to,
            is_negotiable=o.is_negotiable,
            response_count=o.response_count,
            created_at=o.created_at,
        )
        for o in orders
    ]


@router.post("/orders/{order_id}/cancel")
async def admin_cancel_order(
    order_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    o = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    o.status = "cancelled"
    await db.flush()
    return {"ok": True}


@router.get("/chats", response_model=list[AdminChatItem])
async def list_admin_chats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    chats = (await db.execute(
        select(Chat)
        .options(
            selectinload(Chat.client),
            selectinload(Chat.master),
            selectinload(Chat.order),
            selectinload(Chat.messages),
        )
        .order_by(Chat.created_at.desc())
        .limit(100)
    )).scalars().all()
    return [
        AdminChatItem(
            id=c.id,
            order_id=c.order_id,
            order_title=c.order.title if c.order else None,
            client_name=c.client.full_name if c.client else "—",
            master_name=c.master.full_name if c.master else "—",
            message_count=len(c.messages),
            is_confirmed=c.is_collaboration_confirmed,
        )
        for c in chats
    ]
