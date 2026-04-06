from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    text: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order")  # noqa: F821
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id], back_populates="reviews_given")  # noqa: F821
    master: Mapped["User"] = relationship("User", foreign_keys=[master_id], back_populates="reviews_received")  # noqa: F821
