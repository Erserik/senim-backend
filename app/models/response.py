from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    price: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    available_when: Mapped[str | None] = mapped_column(String(50))  # 'Сегодня', 'Завтра', etc

    status: Mapped[str] = mapped_column(String(20), default="waiting", index=True)
    # 'waiting' | 'accepted' | 'completed' | 'declined'

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="responses")  # noqa: F821
    master: Mapped["User"] = relationship("User", back_populates="responses")  # noqa: F821
