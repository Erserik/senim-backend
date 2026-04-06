from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.chat import Chat, Message
from app.models.user import User
from app.schemas.chat import (
    ChatListResponse,
    ChatOut,
    MessageListResponse,
    MessageOut,
    SendMessageRequest,
)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=ChatListResponse)
async def list_chats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all chats for the current user."""
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

    chat_list = []
    for chat in chats:
        # Determine the other user
        if chat.client_id == user.id:
            other = chat.master
        else:
            other = chat.client

        # Get last message
        last_msg = chat.messages[-1] if chat.messages else None
        last_message_text = None
        last_message_time = None
        if last_msg:
            last_message_text = last_msg.text or last_msg.content or ""
            if last_msg.created_at:
                last_message_time = last_msg.created_at.strftime("%H:%M")

        order = chat.order
        chat_list.append(
            ChatOut(
                id=chat.id,
                order_id=chat.order_id,
                other_user_name=other.full_name if other else "Unknown",
                other_user_initials=other.initials if other else "??",
                last_message=last_message_text,
                last_message_time=last_message_time,
                order_title=order.title if order else None,
                order_price=order.budget_display if order else None,
                order_category=order.category_label if order else None,
            )
        )

    return ChatListResponse(chats=chat_list)


@router.get("/{chat_id}/messages", response_model=MessageListResponse)
async def get_messages(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a chat."""
    # Verify user is part of this chat
    result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if chat.client_id != user.id and chat.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your chat")

    # Get messages
    msg_result = await db.execute(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return MessageListResponse(
        messages=[
            MessageOut(
                id=msg.id,
                chat_id=msg.chat_id,
                sender_id=msg.sender_id,
                type="sent" if msg.sender_id == user.id else ("system" if msg.type == "system" else "received"),
                text=msg.text,
                content=msg.content,
                time=msg.created_at.strftime("%H:%M") if msg.created_at else None,
                created_at=msg.created_at,
            )
            for msg in messages
        ]
    )


@router.post("/{chat_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: int,
    req: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message in a chat."""
    result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if chat.client_id != user.id and chat.master_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your chat")

    msg = Message(
        chat_id=chat_id,
        sender_id=user.id,
        type="sent",
        text=req.text,
    )
    db.add(msg)
    await db.flush()

    return MessageOut(
        id=msg.id,
        chat_id=msg.chat_id,
        sender_id=msg.sender_id,
        type="sent",
        text=msg.text,
        content=msg.content,
        time=msg.created_at.strftime("%H:%M") if msg.created_at else None,
        created_at=msg.created_at,
    )
