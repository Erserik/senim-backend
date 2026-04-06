from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order")  # noqa: F821
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id])  # noqa: F821
    master: Mapped["User"] = relationship("User", foreign_keys=[master_id])  # noqa: F821
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="chat", order_by="Message.created_at", lazy="selectin"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), index=True)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    type: Mapped[str] = mapped_column(String(20))  # 'sent' | 'received' | 'system'
    text: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)  # for system messages

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    sender: Mapped["User | None"] = relationship("User")  # noqa: F821
