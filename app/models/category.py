from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    label_ru: Mapped[str] = mapped_column(String(100))
    label_kz: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str] = mapped_column(String(40))
    color: Mapped[str] = mapped_column(String(10))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    subcategories: Mapped[list["Subcategory"]] = relationship(
        "Subcategory",
        back_populates="category",
        order_by="Subcategory.sort_order",
        lazy="selectin",
    )


class Subcategory(Base):
    __tablename__ = "subcategories"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    slug: Mapped[str] = mapped_column(String(80), index=True)
    label_ru: Mapped[str] = mapped_column(String(200))
    label_kz: Mapped[str] = mapped_column(String(200))
    keywords: Mapped[list | None] = mapped_column(JSON, default=list)  # ["протечка", "течёт", ...]
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_other: Mapped[bool] = mapped_column(default=False)

    category: Mapped["Category"] = relationship("Category", back_populates="subcategories")


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name_ru: Mapped[str] = mapped_column(String(100))
    name_kz: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column()
    longitude: Mapped[float | None] = mapped_column()
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    districts: Mapped[list["District"]] = relationship(
        "District", back_populates="city", order_by="District.name_ru", lazy="selectin"
    )


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True)
    slug: Mapped[str] = mapped_column(String(80), index=True)
    name_ru: Mapped[str] = mapped_column(String(100))
    name_kz: Mapped[str] = mapped_column(String(100))

    city: Mapped["City"] = relationship("City", back_populates="districts")
