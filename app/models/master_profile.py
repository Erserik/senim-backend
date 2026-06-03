from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# Tier thresholds and commission rates
TIER_RULES = [
    # (tier, min_orders, min_rating, commission_percent)
    ("gold", 50, 4.7, 5),
    ("silver", 15, 4.2, 7),
    ("bronze", 1, 0.0, 10),
    ("new", 0, 0.0, 10),
]


def compute_tier(order_count: int, rating: float) -> tuple[str, int]:
    """Return (tier_slug, commission_percent) based on master stats."""
    for tier, min_o, min_r, comm in TIER_RULES:
        if order_count >= min_o and rating >= min_r:
            return tier, comm
    return "new", 10


class MasterProfile(Base):
    __tablename__ = "master_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    # Onboarding data (stored as JSON for simplicity)
    specializations: Mapped[list | None] = mapped_column(JSON, default=list)  # list of category slugs
    experience: Mapped[str | None] = mapped_column(String(20))  # 'lt1' | '1to5' | 'gt5'
    bio: Mapped[str | None] = mapped_column(Text)
    portfolio: Mapped[list | None] = mapped_column(JSON, default=list)  # list of image URLs
    districts: Mapped[list | None] = mapped_column(JSON, default=list)  # legacy: list of district slugs
    service_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    service_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    service_radius_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    prices: Mapped[dict | None] = mapped_column(JSON, default=dict)  # {category_slug: {from, to}}

    onboarding_complete: Mapped[bool] = mapped_column(default=False)

    # IIN verification (mock for dev)
    iin: Mapped[str | None] = mapped_column(String(12))
    iin_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Stats
    rating: Mapped[float] = mapped_column(default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    response_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(10), default="new")  # 'new' | 'bronze' | 'silver' | 'gold'
    commission_percent: Mapped[int] = mapped_column(Integer, default=10)

    # Balance (in tenge)
    balance: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship("User", back_populates="master_profile")  # noqa: F821

    def recompute_tier(self) -> None:
        self.tier, self.commission_percent = compute_tier(self.order_count, self.rating)
