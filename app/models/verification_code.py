"""Verification code model for email verification."""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VerificationCode(Base):
    """Email verification code storage.

    Stores temporary verification codes sent to email addresses during registration.
    Codes expire after a configured time period (default 5 minutes).

    Attributes:
        id: Primary key
        email: Email address the code was sent to
        code: 6-digit verification code
        created_at: Timestamp when code was generated
        expires_at: Timestamp when code expires
    """

    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<VerificationCode(email={self.email}, expires_at={self.expires_at})>"
