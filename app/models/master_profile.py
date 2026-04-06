from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MasterProfile(Base):
    __tablename__ = "master_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    # Onboarding data
    specializations: Mapped[list | None] = mapped_column(JSON, default=list)
    experience: Mapped[str | None] = mapped_column(String(20))  # 'beginner' | 'mid' | 'expert'
    bio: Mapped[str | None] = mapped_column(Text)
    portfolio: Mapped[list | None] = mapped_column(JSON, default=list)  # list of image URLs
    districts: Mapped[list | None] = mapped_column(JSON, default=list)  # list of district names
    prices: Mapped[dict | None] = mapped_column(JSON, default=dict)  # {category_id: {from, to}}

    onboarding_complete: Mapped[bool] = mapped_column(default=False)

    # Stats (calculated / cached)
    rating: Mapped[float | None] = mapped_column(default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    response_time_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="master_profile")  # noqa: F821
