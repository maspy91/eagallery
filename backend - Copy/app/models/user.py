import uuid

from sqlalchemy import Boolean, Column, DateTime, String, func

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """
    Single table with a `role` discriminator (admin | staff | customer)
    rather than separate tables -- see the note in the frontend's auth.ts:
    what actually keeps customer and admin/staff accounts from leaking into
    each other is that every query filters by role (customer endpoints only
    ever match role='customer', admin endpoints only ever match role in
    ('admin','staff')), and each side has its own rate-limit bucket and its
    own session cookie. Brute-forcing /api/customer/login can never surface
    or lock out an admin account, because the query never looks at admin
    rows in the first place.
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="customer", index=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def avatar_initials(self) -> str:
        parts = self.name.strip().split()
        if not parts:
            return "?"
        return "".join(p[0] for p in parts[:2]).upper()
