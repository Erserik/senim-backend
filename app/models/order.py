from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    category_slug: Mapped[str] = mapped_column(String(50), index=True)
    category_label_ru: Mapped[str] = mapped_column(String(100))
    category_label_kz: Mapped[str] = mapped_column(String(100), default="")

    subcategory_slug: Mapped[str | None] = mapped_column(String(80), index=True)
    subcategory_label_ru: Mapped[str | None] = mapped_column(String(200))
    subcategory_label_kz: Mapped[str | None] = mapped_column(String(200))

    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    photos: Mapped[list | None] = mapped_column(JSON, default=list)

    city_slug: Mapped[str] = mapped_column(String(50), index=True)
    district_slug: Mapped[str | None] = mapped_column(String(80), index=True)
    district_label_ru: Mapped[str | None] = mapped_column(String(100))
    district_label_kz: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    hide_exact_address: Mapped[bool] = mapped_column(Boolean, default=True)

    date_option: Mapped[str | None] = mapped_column(String(50))  # 'asap' | 'today' | 'tomorrow' | 'date'
    preferred_date: Mapped[str | None] = mapped_column(String(20))  # ISO date string
    time_from: Mapped[str | None] = mapped_column(String(5))  # "HH:MM"
    time_to: Mapped[str | None] = mapped_column(String(5))

    budget_from: Mapped[int | None] = mapped_column(Integer)
    budget_to: Mapped[int | None] = mapped_column(Integer)
    is_negotiable: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    # 'active' | 'in_progress' | 'completed' | 'cancelled'

    selected_response_id: Mapped[int | None] = mapped_column(Integer)
    response_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    is_boosted: Mapped[bool] = mapped_column(Boolean, default=False)
    boosted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    client: Mapped["User"] = relationship("User", back_populates="orders")  # noqa: F821
    responses: Mapped[list["Response"]] = relationship(  # noqa: F821
        "Response", back_populates="order", lazy="selectin"
    )
