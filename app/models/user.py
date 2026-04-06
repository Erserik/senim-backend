from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    photo_url: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(String(10))  # 'client' | 'master'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
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
    reviews_given: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review", foreign_keys="Review.client_id", back_populates="client", lazy="selectin"
    )
    reviews_received: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review", foreign_keys="Review.master_id", back_populates="master", lazy="selectin"
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p)

    @property
    def initials(self) -> str:
        first = (self.first_name or " ")[0].upper()
        last = (self.last_name or " ")[0].upper()
        return f"{first}{last}".strip()


# Import here to avoid circular imports at module level
from app.models.master_profile import MasterProfile  # noqa: E402, F401
