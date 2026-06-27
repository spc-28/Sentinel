"""add past incidents (learning from past incidents)

Revision ID: a1c4e7b90d2f
Revises: 956495874477
Create Date: 2026-07-05 10:22:41.508913

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1c4e7b90d2f'
down_revision: str | None = '956495874477'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'past_incidents',
        sa.Column('service', sa.String(length=255), nullable=False),
        sa.Column('alert_type', sa.String(length=512), nullable=False),
        sa.Column('main_error', sa.Text(), nullable=False),
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.Column('signature_text', sa.Text(), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('root_cause', sa.Text(), nullable=False),
        sa.Column('recommended_fix', sa.Text(), nullable=True),
        sa.Column('investigation_id', sa.Uuid(), nullable=True),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('confirmed_cause', sa.Text(), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('occurrences', sa.Integer(), nullable=False),
        sa.Column('is_pattern', sa.Boolean(), nullable=False),
        sa.Column('pattern_id', sa.Uuid(), nullable=True),
        sa.Column('pattern_label', sa.Text(), nullable=True),
        sa.Column(
            'last_seen_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['pattern_id'], ['past_incidents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_past_incidents_fingerprint'), 'past_incidents', ['fingerprint'], unique=False
    )
    op.create_index(
        op.f('ix_past_incidents_investigation_id'),
        'past_incidents',
        ['investigation_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_past_incidents_pattern_id'), 'past_incidents', ['pattern_id'], unique=False
    )
    op.create_index(op.f('ix_past_incidents_service'), 'past_incidents', ['service'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_past_incidents_service'), table_name='past_incidents')
    op.drop_index(op.f('ix_past_incidents_pattern_id'), table_name='past_incidents')
    op.drop_index(op.f('ix_past_incidents_investigation_id'), table_name='past_incidents')
    op.drop_index(op.f('ix_past_incidents_fingerprint'), table_name='past_incidents')
    op.drop_table('past_incidents')
