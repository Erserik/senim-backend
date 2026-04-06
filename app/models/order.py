from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    category_slug: Mapped[str] = mapped_column(String(50), index=True)
    category_label: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    photos: Mapped[list | None] = mapped_column(JSON, default=list)

    district: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(300))

    date_option: Mapped[str | None] = mapped_column(String(50))  # 'Сегодня', 'Завтра', custom
    time_option: Mapped[str | None] = mapped_column(String(50))  # 'morning', 'afternoon', 'evening'

    budget_from: Mapped[int | None] = mapped_column(Integer)
    budget_to: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    # 'active' | 'in_progress' | 'completed' | 'cancelled'

    response_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    client: Mapped["User"] = relationship("User", back_populates="orders")  # noqa: F821
    responses: Mapped[list["Response"]] = relationship(  # noqa: F821
        "Response", back_populates="order", lazy="selectin"
    )

    @property
    def budget_display(self) -> str:
        if self.budget_from and self.budget_to:
            if self.budget_from == self.budget_to:
                return f"{self.budget_from:,} тг".replace(",", " ")
            return f"{self.budget_from:,} – {self.budget_to:,} тг".replace(",", " ")
        if self.budget_from:
            return f"от {self.budget_from:,} тг".replace(",", " ")
        if self.budget_to:
            return f"до {self.budget_to:,} тг".replace(",", " ")
        return "Договорная"
