from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("order_id", "master_id", name="uq_response_order_master"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    price: Mapped[int] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    availability: Mapped[str | None] = mapped_column(String(30))
    # 'today' | 'tomorrow' | 'this_week' | 'discuss'

    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # 'pending' | 'viewed' | 'accepted' | 'rejected' | 'retracted'

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    order: Mapped["Order"] = relationship("Order", back_populates="responses")  # noqa: F821
    master: Mapped["User"] = relationship("User", back_populates="responses")  # noqa: F821
