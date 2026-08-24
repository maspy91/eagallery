"""photo_views (deduped view counting)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photo_views",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("photo_id", sa.String(length=36), sa.ForeignKey("photos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("viewer_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("photo_id", "viewer_key", name="uq_photo_views_photo_viewer"),
    )
    op.create_index("ix_photo_views_photo_id", "photo_views", ["photo_id"])
    op.create_index("ix_photo_views_viewer_key", "photo_views", ["viewer_key"])


def downgrade() -> None:
    op.drop_table("photo_views")
