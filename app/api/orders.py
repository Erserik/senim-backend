import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.category import Category, District, Subcategory
from app.models.chat import Chat, Message
from app.models.order import Order
from app.models.response import Response
from app.models.user import User
from app.schemas.order import (
    OrderBrief,
    OrderCreateRequest,
    OrderDetail,
    OrderListResponse,
    ResponsePreview,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _category_bits(category: Category) -> tuple[str, str]:
    return category.icon, category.color


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def _order_to_brief(order: Order, db: AsyncSession, viewer_id: int | None = None) -> OrderBrief:
    cat = (await db.execute(
        select(Category).where(Category.slug == order.category_slug)
    )).scalar_one_or_none()

    # Address visibility:
    #  - always visible to the client who owns the order
    #  - visible to the selected master (after acceptance)
    #  - visible to anyone if hide_exact_address is False
    show_address = not order.hide_exact_address
    if viewer_id is not None:
        if viewer_id == order.client_id:
            show_address = True
        elif order.selected_response_id:
            sel = (await db.execute(
                select(Response).where(Response.id == order.selected_response_id)
            )).scalar_one_or_none()
            if sel and sel.master_id == viewer_id:
                show_address = True

    return OrderBrief(
        id=order.id,
        client_id=order.client_id,
        category_slug=order.category_slug,
        category_label_ru=order.category_label_ru,
        category_label_kz=order.category_label_kz,
        category_icon=cat.icon if cat else None,
        category_color=cat.color if cat else None,
        subcategory_slug=order.subcategory_slug,
        subcategory_label_ru=order.subcategory_label_ru,
        subcategory_label_kz=order.subcategory_label_kz,
        title=order.title,
        description=order.description,
        photos=order.photos or [],
        city_slug=order.city_slug,
        district_slug=order.district_slug,
        district_label_ru=order.district_label_ru,
        district_label_kz=order.district_label_kz,
        address=order.address if show_address else None,
        latitude=order.latitude,
        longitude=order.longitude,
        hide_exact_address=order.hide_exact_address,
        date_option=order.date_option,
        preferred_date=order.preferred_date,
        time_from=order.time_from,
        time_to=order.time_to,
        budget_from=order.budget_from,
        budget_to=order.budget_to,
        is_negotiable=order.is_negotiable,
        status=order.status,
        response_count=order.response_count,
        view_count=order.view_count,
        selected_response_id=order.selected_response_id,
        is_boosted=bool(order.is_boosted and (order.boosted_until is None or order.boosted_until > datetime.now(timezone.utc))),
        boosted_until=order.boosted_until,
        created_at=order.created_at,
        completed_at=order.completed_at,
    )


def _response_to_preview(resp: Response, master: User) -> ResponsePreview:
    mp = master.master_profile
    return ResponsePreview(
        id=resp.id,
        master_id=resp.master_id,
        master_name=master.full_name or "Мастер",
        master_initials=master.initials,
        master_photo=master.photo_url,
        master_rating=(mp.rating if mp else 0.0) or 0.0,
        master_review_count=(mp.review_count if mp else 0) or 0,
        master_order_count=(mp.order_count if mp else 0) or 0,
        master_tier=(mp.tier if mp else "new") or "new",
        master_portfolio=(mp.portfolio if mp else []) or [],
        price=resp.price,
        message=resp.message,
        availability=resp.availability,
        status=resp.status,
        created_at=resp.created_at,
    )


@router.get("", response_model=OrderListResponse)
async def list_orders(
    category: str | None = Query(None),
    city: str | None = Query(None),
    district: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    only_my_categories: bool = Query(False),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Feed for masters — active orders, filterable by category/city/district."""
    now = datetime.now(timezone.utc)
    boost_active = (Order.is_boosted.is_(True)) & (
        (Order.boosted_until.is_(None)) | (Order.boosted_until > now)
    )
    query = select(Order).order_by(boost_active.desc(), Order.created_at.desc())
    query = query.where(Order.status == (status_filter or "active"))

    if category:
        query = query.where(Order.category_slug == category)
    if city:
        query = query.where(Order.city_slug == city)
    if district:
        query = query.where(Order.district_slug == district)

    from app.models.master_profile import MasterProfile
    mp = (await db.execute(
        select(MasterProfile).where(MasterProfile.user_id == user.id)
    )).scalar_one_or_none()

    if only_my_categories and mp and mp.specializations:
        query = query.where(Order.category_slug.in_(mp.specializations))

    area_lat = mp.service_lat if mp else None
    area_lng = mp.service_lng if mp else None
    area_r = mp.service_radius_km if mp else None
    if area_lat is not None and area_lng is not None and area_r:
        # Rough bounding-box prefilter (1° lat ≈ 111 km); orders must have coords to be in range.
        lat_delta = area_r / 111.0
        lng_delta = area_r / (111.0 * max(math.cos(math.radians(area_lat)), 0.1))
        query = query.where(
            Order.latitude.is_not(None),
            Order.longitude.is_not(None),
            Order.latitude.between(area_lat - lat_delta, area_lat + lat_delta),
            Order.longitude.between(area_lng - lng_delta, area_lng + lng_delta),
        )

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (await db.execute(query.offset(offset).limit(limit))).scalars().all()

    if area_lat is not None and area_lng is not None and area_r:
        rows = [
            o for o in rows
            if o.latitude is not None and o.longitude is not None
            and _haversine_km(area_lat, area_lng, o.latitude, o.longitude) <= area_r
        ]

    return OrderListResponse(
        orders=[await _order_to_brief(o, db, user.id) for o in rows],
        total=total,
    )


@router.get("/my", response_model=OrderListResponse)
async def list_my_orders(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Orders created by the current client."""
    query = select(Order).where(Order.client_id == user.id).order_by(Order.created_at.desc())
    if status_filter:
        if status_filter == "active_with_proposals":
            query = query.where(Order.status.in_(["active", "in_progress"]))
        elif status_filter == "archive":
            query = query.where(Order.status.in_(["completed", "cancelled"]))
        else:
            query = query.where(Order.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (await db.execute(query.offset(offset).limit(limit))).scalars().all()

    return OrderListResponse(
        orders=[await _order_to_brief(o, db, user.id) for o in rows],
        total=total,
    )


@router.post("", response_model=OrderBrief, status_code=status.HTTP_201_CREATED)
async def create_order(
    req: OrderCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clients can create orders")

    cat = (await db.execute(
        select(Category).where(Category.slug == req.category_slug)
    )).scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category")

    sub = None
    if req.subcategory_slug:
        sub = (await db.execute(
            select(Subcategory).where(
                and_(
                    Subcategory.category_id == cat.id,
                    Subcategory.slug == req.subcategory_slug,
                )
            )
        )).scalar_one_or_none()

    district = None
    if req.district_slug:
        district = (await db.execute(
            select(District).where(
                and_(District.slug == req.district_slug),
            )
        )).scalar_one_or_none()

    order = Order(
        client_id=user.id,
        category_slug=cat.slug,
        category_label_ru=cat.label_ru,
        category_label_kz=cat.label_kz,
        subcategory_slug=sub.slug if sub else None,
        subcategory_label_ru=sub.label_ru if sub else None,
        subcategory_label_kz=sub.label_kz if sub else None,
        title=req.title,
        description=req.description,
        photos=req.photos,
        city_slug=req.city_slug,
        district_slug=district.slug if district else None,
        district_label_ru=district.name_ru if district else None,
        district_label_kz=district.name_kz if district else None,
        address=req.address,
        latitude=req.latitude,
        longitude=req.longitude,
        hide_exact_address=req.hide_exact_address,
        date_option=req.date_option,
        preferred_date=req.preferred_date,
        time_from=req.time_from,
        time_to=req.time_to,
        budget_from=req.budget_from,
        budget_to=req.budget_to,
        is_negotiable=req.is_negotiable,
        status="active",
    )
    db.add(order)
    await db.flush()
    return await _order_to_brief(order, db, user.id)


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.responses).selectinload(Response.master).selectinload(User.master_profile),
            selectinload(Order.client),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    brief = await _order_to_brief(order, db, user.id)

    is_client = order.client_id == user.id
    my_response: ResponsePreview | None = None
    all_responses: list[ResponsePreview] = []

    for r in order.responses:
        if r.master_id == user.id:
            my_response = _response_to_preview(r, r.master)
        if is_client:
            all_responses.append(_response_to_preview(r, r.master))

    # Check if this master (if any) has a confirmed chat to see client phone
    client = order.client
    client_phone = None
    if not is_client and my_response:
        chat = (await db.execute(
            select(Chat).where(
                and_(Chat.order_id == order.id, Chat.master_id == user.id)
            )
        )).scalar_one_or_none()
        if chat and chat.is_collaboration_confirmed and client.phone_visible_after_deal:
            client_phone = client.phone

    # Increment view count if viewed by non-owner master
    if not is_client and user.role == "master":
        order.view_count += 1
        await db.flush()

    return OrderDetail(
        **brief.model_dump(),
        client_name=client.full_name if client else None,
        client_initials=client.initials if client else None,
        client_photo=client.photo_url if client else None,
        client_rating=client.client_rating if client else 0.0,
        client_review_count=client.client_review_count if client else 0,
        client_phone=client_phone,
        my_response=my_response,
        responses=all_responses,
    )


@router.post("/{order_id}/boost", response_model=OrderBrief)
async def boost_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    if order.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only active orders can be boosted")

    from datetime import timedelta
    order.is_boosted = True
    order.boosted_until = datetime.now(timezone.utc) + timedelta(hours=24)
    await db.flush()
    return await _order_to_brief(order, db, user.id)


@router.post("/{order_id}/cancel", response_model=OrderBrief)
async def cancel_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    if order.status not in ("active", "in_progress"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel")

    order.status = "cancelled"
    await db.flush()
    return await _order_to_brief(order, db, user.id)


@router.post("/{order_id}/complete", response_model=OrderBrief)
async def complete_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
    if order.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is not in progress")

    order.status = "completed"
    order.completed_at = datetime.now(timezone.utc)

    # Post system message in chat
    chat = (await db.execute(select(Chat).where(Chat.order_id == order.id))).scalar_one_or_none()
    if chat:
        db.add(Message(
            chat_id=chat.id,
            sender_id=None,
            type="system",
            system_kind="order_completed",
            text="Заказ завершён. Оставьте отзыв и чаевые.",
        ))

    await db.flush()
    return await _order_to_brief(order, db, user.id)
