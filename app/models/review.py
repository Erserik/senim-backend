from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    direction: Mapped[str] = mapped_column(String(20))  # 'client_to_master' | 'master_to_client'

    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    text: Mapped[str | None] = mapped_column(Text)
    tip_amount: Mapped[int] = mapped_column(Integer, default=0)  # tenge

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id])  # noqa: F821
    target: Mapped["User"] = relationship("User", foreign_keys=[target_id])  # noqa: F821
