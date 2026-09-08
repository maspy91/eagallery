"""add conversation quotes

Revision ID: b8c76c83c4bf
Revises: c85db6002d9e
Create Date: 2026-09-03 07:06:50.459792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c76c83c4bf'
down_revision: Union[str, None] = 'c85db6002d9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('conversation_quotes',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('conversation_id', sa.String(length=36), nullable=False),
    sa.Column('created_by_id', sa.String(length=36), nullable=True),
    sa.Column('created_by_name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('amount_cents', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_conversation_quotes_conversation_id'), 'conversation_quotes', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_quotes_status'), 'conversation_quotes', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_conversation_quotes_status'), table_name='conversation_quotes')
    op.drop_index(op.f('ix_conversation_quotes_conversation_id'), table_name='conversation_quotes')
    op.drop_table('conversation_quotes')
