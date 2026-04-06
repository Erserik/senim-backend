from datetime import datetime

from pydantic import BaseModel, Field


class ChatOut(BaseModel):
    id: int
    order_id: int
    other_user_name: str
    other_user_initials: str
    other_user_online: bool = False
    last_message: str | None = None
    last_message_time: str | None = None
    order_title: str | None = None
    order_price: str | None = None
    order_category: str | None = None

    model_config = {"from_attributes": True}


class ChatListResponse(BaseModel):
    chats: list[ChatOut]


class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int | None
    type: str  # 'sent' | 'received' | 'system'
    text: str | None
    content: str | None
    time: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    messages: list[MessageOut]


class SendMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
