from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csv_export import EXPORT_ROW_LIMIT, csv_response, parse_date_range
from app.core.database import get_db
from app.core.deps import require_permission
from app.models.user import User
from app.schemas.customers import CustomerOut, CustomerStatsOut, CustomerStatusRequest

# Admin-only (customers:manage) -- staff have plenty of day-to-day
# customer-facing capability already (comments:moderate, requests:respond,
# the chat queue), but account-level control over someone else's account
# (deactivating it) is kept at the same tier as roles:manage, not handed
# to every staff member by default.
router = APIRouter(prefix="/api/customers", tags=["customers"], dependencies=[Depends(require_permission("customers:manage"))])


def _customer_out(user: User) -> CustomerOut:
    return CustomerOut(
        id=user.id,
        email=user.email,
        name=user.name,
        avatarInitials=user.avatar_initials,
        emailVerified=user.email_verified,
        isActive=user.is_active,
        createdAt=user.created_at.isoformat() if user.created_at else "",
    )


def _apply_customer_filters(query, *, q: str | None, is_active: bool | None, date_from: str | None, date_to: str | None):
    if q:
        like = f"%{q}%"
        query = query.where(or_(User.name.ilike(like), User.email.ilike(like)))

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    parsed_from, parsed_to = parse_date_range(date_from, date_to)
    if parsed_from:
        query = query.where(User.created_at >= parsed_from)
    if parsed_to:
        query = query.where(User.created_at <= parsed_to)

    return query


@router.get("", response_model=list[CustomerOut])
async def list_customers(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, max_length=255, description="Search by name or email"),
    is_active: bool | None = Query(default=None),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD, inclusive"),
    limit: int = Query(default=50, ge=1, le=100),
):
    query = _apply_customer_filters(
        select(User).where(User.role == "customer"), q=q, is_active=is_active, date_from=date_from, date_to=date_to
    )
    query = query.order_by(User.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return [_customer_out(u) for u in result.scalars().all()]


@router.get("/export")
async def export_customers(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """CSV of customers matching the same filters as the list endpoint."""
    query = _apply_customer_filters(
        select(User).where(User.role == "customer"), q=q, is_active=is_active, date_from=date_from, date_to=date_to
    )
    query = query.order_by(User.created_at.desc()).limit(EXPORT_ROW_LIMIT)

    result = await db.execute(query)
    customers = result.scalars().all()

    rows = (
        [
            u.id,
            u.name,
            u.email,
            "yes" if u.email_verified else "no",
            "active" if u.is_active else "deactivated",
            u.created_at.isoformat() if u.created_at else "",
        ]
        for u in customers
    )
    return csv_response(
        "customers.csv", ["ID", "Name", "Email", "Email Verified", "Status", "Created At"], rows
    )


@router.get("/stats", response_model=CustomerStatsOut)
async def get_customer_stats(db: AsyncSession = Depends(get_db)):
    """Total registered customer count -- SQL COUNT, same reasoning as
    the other /stats endpoints added alongside the admin dashboard
    overview (see routers/photos.py's get_photo_stats)."""
    result = await db.execute(select(func.count()).select_from(User).where(User.role == "customer"))
    return CustomerStatsOut(totalCount=result.scalar_one())


@router.patch("/{customer_id}", response_model=CustomerOut)
async def set_customer_status(customer_id: str, payload: CustomerStatusRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == customer_id, User.role == "customer"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")

    user.is_active = payload.isActive
    await db.commit()
    await db.refresh(user)
    return _customer_out(user)
