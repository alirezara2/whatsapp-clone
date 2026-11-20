from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, func, UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("owner_id", "contact_id", name="uq_owner_contact"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str | None] = mapped_column(String(100), nullable=True)  # اسم دلخواه

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], back_populates="contacts")
    contact: Mapped["User"] = relationship("User", foreign_keys=[contact_id])