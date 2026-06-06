"""Add section_payment_initiations table

Revision ID: c1b2f3d4e5a6
Revises: b47280a5936c
Create Date: 2026-06-05 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1b2f3d4e5a6"
down_revision: Union[str, None] = "b47280a5936c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "section_payment_initiations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("section_id", sa.String(length=36), nullable=False),
        sa.Column("payment_initiated", sa.Boolean(), nullable=False),
        sa.Column("is_paid", sa.Boolean(), nullable=False),
        sa.Column("payment_link", sa.Text(), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_spi_user_id"), "section_payment_initiations", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_spi_event_id"), "section_payment_initiations", ["event_id"], unique=False
    )
    op.create_index(
        op.f("ix_spi_section_id"), "section_payment_initiations", ["section_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_spi_section_id"), table_name="section_payment_initiations")
    op.drop_index(op.f("ix_spi_event_id"), table_name="section_payment_initiations")
    op.drop_index(op.f("ix_spi_user_id"), table_name="section_payment_initiations")
    op.drop_table("section_payment_initiations")
