import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class AuthToken(Base):
    """
    Single-use, short-lived tokens for the three flows that need them:
    email_verify, password_reset, staff_invite. Only the SHA-256 hash of
    the raw token is stored -- the raw token is emailed once and never
    persisted -- so a leaked database dump can't be replayed as valid
    links (same reasoning as storing password hashes, not passwords).

    `user_id` is null for staff_invite tokens, since the invited person
    doesn't have a User row yet; `email`/`invite_name`/`invite_role` carry
    what's needed to create that row when the invite is accepted.
    """

    __tablename__ = "auth_tokens"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    email = Column(String(255), nullable=True)  # staff_invite only

    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    purpose = Column(String(30), nullable=False, index=True)  # email_verify | password_reset | staff_invite

    invite_name = Column(String(100), nullable=True)
    invite_role = Column(String(20), nullable=True)  # currently always "staff"

    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
