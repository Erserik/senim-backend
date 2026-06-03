from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    city_slug: Mapped[str | None] = mapped_column(String(50), index=True)
    photo_url: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(String(10))  # 'client' | 'master'

    # Privacy
    phone_visible_after_deal: Mapped[bool] = mapped_column(Boolean, default=True)
    online_status_visible: Mapped[bool] = mapped_column(Boolean, default=True)

    # Preferences
    language: Mapped[str] = mapped_column(String(2), default="ru")  # 'ru' | 'kz'

    # Client-side rating (as-client, reviewed by masters)
    client_rating: Mapped[float] = mapped_column(default=0.0)
    client_review_count: Mapped[int] = mapped_column(Integer, default=0)
    client_order_count: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    master_profile: Mapped["MasterProfile | None"] = relationship(
        "MasterProfile", back_populates="user", uselist=False, lazy="selectin"
    )
    orders: Mapped[list["Order"]] = relationship(  # noqa: F821
        "Order", back_populates="client", lazy="selectin"
    )
    responses: Mapped[list["Response"]] = relationship(  # noqa: F821
        "Response", back_populates="master", lazy="selectin"
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p)

    @property
    def initials(self) -> str:
        first = (self.first_name or " ")[0].upper() if self.first_name else ""
        last = (self.last_name or " ")[0].upper() if self.last_name else ""
        return f"{first}{last}".strip() or "?"


from app.models.master_profile import MasterProfile  # noqa: E402, F401
