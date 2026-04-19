from datetime import datetime

from pydantic import BaseModel


class ChatBrief(BaseModel):
    id: int
    order_id: int
    order_title: str | None = None
    order_category_slug: str | None = None
    order_category_label_ru: str | None = None
    order_category_label_kz: str | None = None
    order_price_display: str | None = None
    other_user_id: int
    other_user_name: str
    other_user_initials: str
    other_user_photo: str | None = None
    other_user_online: bool = True
    last_message: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0
    client_confirmed: bool = False
    master_confirmed: bool = False
    is_collaboration_confirmed: bool = False
    phone_revealed: str | None = None


class ChatListResponse(BaseModel):
    chats: list[ChatBrief]


class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int | None
    direction: str
    type: str
    text: str | None = None
    photo_url: str | None = None
    system_kind: str | None = None
    created_at: datetime


class ChatDetail(ChatBrief):
    messages: list[MessageOut] = []


class MessageListResponse(BaseModel):
    messages: list[MessageOut]


class SendMessageRequest(BaseModel):
    text: str | None = None
    photo_url: str | None = None
