from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.chat import Chat, Message
from app.models.user import User
from app.schemas.chat import (
    ChatBrief,
    ChatDetail,
    ChatListResponse,
    MessageListResponse,
    MessageOut,
    SendMessageRequest,
)

router = APIRouter(prefix="/chats", tags=["chats"])


def _budget_display(order) -> str | None:
    if not order:
        return None
    if order.is_negotiable:
        return "Договорная"
    if order.budget_from and order.budget_to:
        if order.budget_from == order.budget_to:
            return f"{order.budget_from:,} тг".replace(",", " ")
        return f"{order.budget_from:,} – {order.budget_to:,} тг".replace(",", " ")
    if order.budget_from:
        return f"от {order.budget_from:,} тг".replace(",", " ")
    return None


def _message_to_out(msg: Message, user_id: int) -> MessageOut:
    if msg.type == "system":
        direction = "system"
    else:
        direction = "sent" if msg.sender_id == user_id else "received"
    return MessageOut(
        id=msg.id,
        chat_id=msg.chat_id,
        sender_id=msg.sender_id,
        direction=direction,
        type=msg.type,
        text=msg.text,
        photo_url=msg.photo_url,
        system_kind=msg.system_kind,
        created_at=msg.created_at,
    )


def _chat_to_brief(chat: Chat, user: User) -> ChatBrief:
    is_client = chat.client_id == user.id
    other = chat.master if is_client else chat.client
    order = chat.order

    last_msg = chat.messages[-1] if chat.messages else None
    last_text = None
    last_at = None
    if last_msg:
        if last_msg.type == "system":
            last_text = last_msg.text or "Системное сообщение"
        else:
            last_text = last_msg.text or ("Фото" if last_msg.photo_url else "")
        last_at = last_msg.created_at

    unread = sum(
        1 for m in chat.messages
        if m.sender_id != user.id and not m.is_read and m.type != "system"
    )

    client_confirmed = chat.client_confirmed_at is not None
    master_confirmed = chat.master_confirmed_at is not None
    is_confirmed = client_confirmed and master_confirmed

    phone_revealed = None
    if is_confirmed:
        # Show the other party's phone to this user, respecting privacy toggles
        if is_client:
            phone_revealed = other.phone if other else None
        else:
            # Master sees client phone only if client allows it
            if chat.client and chat.client.phone_visible_after_deal:
                phone_revealed = chat.client.phone

    return ChatBrief(
        id=chat.id,
        order_id=chat.order_id,
        order_title=order.title if order else None,
        order_category_slug=order.category_slug if order else None,
        order_category_label_ru=order.category_label_ru if order else None,
        order_category_label_kz=order.category_label_kz if order else None,
        order_price_display=_budget_display(order),
        other_user_id=other.id if other else 0,
        other_user_name=other.full_name if other else "Unknown",
        other_user_initials=other.initials if other else "??",
        other_user_photo=other.photo_url if other else None,
        other_user_online=(other.online_status_visible if other else True),
        last_message=last_text,
        last_message_at=last_at,
        unread_count=unread,
        client_confirmed=client_confirmed,
        master_confirmed=master_confirmed,
        is_collaboration_confirmed=is_confirmed,
        phone_revealed=phone_revealed,
    )


@router.get("", response_model=ChatListResponse)
async def list_chats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chat)
        .options(
            selectinload(Chat.client),
            selectinload(Chat.master),
            selectinload(Chat.order),
            selectinload(Chat.messages),
        )
        .where(or_(Chat.client_id == user.id, Chat.master_id == user.id))
        .order_by(Chat.created_at.desc())
    )
    chats = result.scalars().all()
    return ChatListResponse(chats=[_chat_to_brief(c, user) for c in chats])


@router.get("/{chat_id}", response_model=ChatDetail)
async def get_chat(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chat)
        .options(
            selectinload(Chat.client),
            selectinload(Chat.master),
            selectinload(Chat.order),
            selectinload(Chat.messages),
        )
        .where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if chat.client_id != user.id and chat.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your chat")

    # Mark inbound messages as read
    for m in chat.messages:
        if m.sender_id != user.id and not m.is_read:
            m.is_read = True
    await db.flush()

    brief = _chat_to_brief(chat, user)
    return ChatDetail(
        **brief.model_dump(),
        messages=[_message_to_out(m, user.id) for m in chat.messages],
    )


@router.get("/{chat_id}/messages", response_model=MessageListResponse)
async def get_messages(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if chat.client_id != user.id and chat.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your chat")

    msgs = (await db.execute(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    )).scalars().all()
    for m in msgs:
        if m.sender_id != user.id and not m.is_read:
            m.is_read = True
    await db.flush()

    return MessageListResponse(messages=[_message_to_out(m, user.id) for m in msgs])


@router.post("/{chat_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: int,
    req: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if chat.client_id != user.id and chat.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your chat")
    if not (req.text or req.photo_url):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty message")

    msg = Message(
        chat_id=chat_id,
        sender_id=user.id,
        type="photo" if req.photo_url else "text",
        text=req.text,
        photo_url=req.photo_url,
    )
    db.add(msg)
    await db.flush()
    return _message_to_out(msg, user.id)


@router.post("/{chat_id}/confirm", response_model=ChatBrief)
async def confirm_collaboration(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chat)
        .options(
            selectinload(Chat.client),
            selectinload(Chat.master),
            selectinload(Chat.order),
            selectinload(Chat.messages),
        )
        .where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if chat.client_id != user.id and chat.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your chat")

    now = datetime.now(timezone.utc)
    is_client = chat.client_id == user.id
    if is_client and chat.client_confirmed_at is None:
        chat.client_confirmed_at = now
    if not is_client and chat.master_confirmed_at is None:
        chat.master_confirmed_at = now
    await db.flush()

    # If mutually confirmed, post system message with phone(s)
    if (
        chat.client_confirmed_at is not None
        and chat.master_confirmed_at is not None
        and not any(
            m.system_kind == "collaboration_confirmed" for m in chat.messages
        )
    ):
        phone_for_master = (
            chat.client.phone if chat.client and chat.client.phone_visible_after_deal else None
        )
        phone_for_client = chat.master.phone if chat.master else None
        text = "Сотрудничество подтверждено."
        if phone_for_master:
            text += f" Телефон клиента: {phone_for_master}."
        if phone_for_client:
            text += f" Телефон мастера: {phone_for_client}."
        db.add(Message(
            chat_id=chat.id,
            sender_id=None,
            type="system",
            system_kind="collaboration_confirmed",
            text=text,
        ))
        await db.flush()

    # Re-fetch to get fresh messages list
    result = await db.execute(
        select(Chat)
        .options(
            selectinload(Chat.client),
            selectinload(Chat.master),
            selectinload(Chat.order),
            selectinload(Chat.messages),
        )
        .where(Chat.id == chat_id)
    )
    chat = result.scalar_one()
    return _chat_to_brief(chat, user)
