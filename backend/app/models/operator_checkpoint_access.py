import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.guid import GUID


class OperatorCheckpointAccess(Base):
    __tablename__ = "operator_checkpoint_access"
    __table_args__ = (
        UniqueConstraint("user_id", "checkpoint_id", name="uq_operator_checkpoint_access_user_checkpoint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    checkpoint_id: Mapped[str] = mapped_column(String(64), nullable=False)

    user = relationship("User", back_populates="checkpoint_access")
