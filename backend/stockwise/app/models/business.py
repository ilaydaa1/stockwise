import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockwise.app.db.base import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="TRY",
    )

    timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Europe/Istanbul",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="business",
    )

    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="business",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            name="uq_business_owner_id",
        ),
        Index(
            "ix_businesses_owner_id",
            "owner_id",
        ),
    )

    def __repr__(self) -> str:
        return f"<Business {self.name} owner={self.owner_id}>"