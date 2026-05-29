"""batch verifications table

Revision ID: 002
Revises: 001
Create Date: 2026-05-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "batch_verifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("collector_id", sa.Integer(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("berat_lapangan_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("berat_received_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("berat_karantina_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("berat_reweighing_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("berat_final_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("kadar_air_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("kelembapan_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("susut_received_to_quarantine_pct", sa.Numeric(8, 3), nullable=True),
        sa.Column("susut_lapangan_to_final_pct", sa.Numeric(8, 3), nullable=True),
        sa.Column("yield_pct", sa.Numeric(8, 3), nullable=True),
        sa.Column("risk_level", sa.String(length=16), server_default="LOW", nullable=False),
        sa.Column("flags_json", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quarantine_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reweighing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("regrading_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"]),
        sa.ForeignKeyConstraint(["collector_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id"),
    )
    op.create_index("ix_batch_verifications_batch_id", "batch_verifications", ["batch_id"])


def downgrade() -> None:
    op.drop_table("batch_verifications")
