from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    response_id: Mapped[int | None] = mapped_column(ForeignKey("responses.id"))

    # Mutual collaboration confirmation
    client_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    master_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    order: Mapped["Order"] = relationship("Order")  # noqa: F821
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id])  # noqa: F821
    master: Mapped["User"] = relationship("User", foreign_keys=[master_id])  # noqa: F821
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="chat", order_by="Message.created_at", lazy="selectin"
    )

    @property
    def is_collaboration_confirmed(self) -> bool:
        return self.client_confirmed_at is not None and self.master_confirmed_at is not None


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), index=True)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    type: Mapped[str] = mapped_column(String(20), default="text")
    # 'text' | 'photo' | 'system'
    text: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    system_kind: Mapped[str | None] = mapped_column(String(40))
    # 'proposal_accepted' | 'collaboration_confirmed' | 'order_completed' | 'day_divider'

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    sender: Mapped["User | None"] = relationship("User")  # noqa: F821
