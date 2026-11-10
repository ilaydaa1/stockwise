import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from stockwise.app.db.base import Base
from stockwise.app.db.ids import new_uuid


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=new_uuid,
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "name",
            name="uq_categories_business_name",
        ),
        # Target of the composite foreign key on products, which
        # guarantees a product and its category share a business.
        UniqueConstraint(
            "business_id",
            "id",
            name="uq_categories_business_id_id",
        ),
    )

    def __repr__(self) -> str:
        return f"<Category {self.name}>"
