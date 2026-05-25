"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("MOBILE_USER", "ADMIN", "SUPERADMIN", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=64), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id"),
    )

    batch_status = sa.Enum(
        "DRAFT", "UPLOADED", "RECEIVED", "QUARANTINE", "REWEIGHING",
        "REGRADING", "FINALIZED", "REJECTED", "CANCELLED",
        name="batch_status",
    )
    deal_type = sa.Enum("KLASIFIKASI", "CONG", name="deal_type")
    payment_method = sa.Enum("CASH", "TRANSFER", name="payment_method")

    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("batch_code", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("farmer_name", sa.String(length=255), nullable=False),
        sa.Column("farmer_location", sa.String(length=512), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("deal_type", deal_type, nullable=False),
        sa.Column("mobile_estimated_total_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("mobile_estimated_total_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("payment_method", payment_method, nullable=True),
        sa.Column("payment_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("operational_cost_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("status", batch_status, nullable=False),
        sa.Column("server_created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("server_updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_version", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_uuid"),
    )

    item_type = sa.Enum("MANGKUK", "SUDUT", "PATAHAN", "CONG", name="item_type")
    source_type = sa.Enum("MOBILE_ESTIMATE", "ADMIN_FINAL", name="source_type")
    cost_type = sa.Enum("TRANSPORT", "MAKAN", "PENGINAPAN", "PENGIRIMAN", "LAIN_LAIN", name="cost_type")
    batch_payment_method = sa.Enum("CASH", "TRANSFER", name="batch_payment_method")

    op.create_table(
        "batch_purchase_details",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("item_type", item_type, nullable=False),
        sa.Column("weight_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("price_per_kg", sa.Numeric(18, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_uuid"], ["batches.batch_uuid"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "batch_costs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("cost_type", cost_type, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_uuid"], ["batches.batch_uuid"]),
        sa.PrimaryKeyConstraint("id"),
    )

    file_type = sa.Enum("SOP_PHOTO", "TRANSFER_RECEIPT", "OTHER", name="file_type")
    photo_type = sa.Enum("UTUH", "CLOSE_UP_SERAT", "AREA_KOTORAN", "SAMPING", name="photo_type")

    op.create_table(
        "batch_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_uuid", sa.String(length=36), nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("file_type", file_type, nullable=False),
        sa.Column("photo_type", photo_type, nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("stored_filename", sa.String(length=512), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_uuid"], ["batches.batch_uuid"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_uuid"),
    )

    op.create_table(
        "batch_payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("method", batch_payment_method, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("receipt_file_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_uuid"], ["batches.batch_uuid"]),
        sa.ForeignKeyConstraint(["receipt_file_id"], ["batch_files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    grade_type = sa.Enum("MANGKUK", "SUDUT", "PATAHAN", "CONG", "REJECT", name="grade_type")
    lot_status = sa.Enum("VERIFIED", "SOLD", "ADJUSTED", "CANCELLED", name="lot_status")
    lot_grade_type = sa.Enum("MANGKUK", "SUDUT", "PATAHAN", "CONG", "REJECT", name="lot_grade_type")

    op.create_table(
        "reweighing_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("gross_weight_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("tare_weight_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("net_weight_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("shrinkage_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("moisture_note", sa.Text(), nullable=True),
        sa.Column("operator_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_uuid"], ["batches.batch_uuid"]),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "regrading_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("grade_type", grade_type, nullable=False),
        sa.Column("weight_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("quality_note", sa.Text(), nullable=True),
        sa.Column("defect_note", sa.Text(), nullable=True),
        sa.Column("operator_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_uuid"], ["batches.batch_uuid"]),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "inventory_lots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("lot_code", sa.String(length=64), nullable=False),
        sa.Column("grade_type", lot_grade_type, nullable=False),
        sa.Column("final_weight_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("cost_basis", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", lot_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_uuid"], ["batches.batch_uuid"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lot_code"),
    )

    op.create_table(
        "status_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("old_status", batch_status, nullable=True),
        sa.Column("new_status", batch_status, nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_uuid"], ["batches.batch_uuid"]),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sync_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_uuid", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_uuid", sa.String(length=36), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    for table in [
        "audit_logs", "sync_events", "status_history", "inventory_lots",
        "regrading_records", "reweighing_records", "batch_payments",
        "batch_files", "batch_costs", "batch_purchase_details", "batches",
        "devices", "users",
    ]:
        op.drop_table(table)
    for enum in [
        "lot_grade_type", "lot_status", "grade_type", "photo_type", "file_type",
        "batch_payment_method", "cost_type", "source_type", "item_type",
        "batch_status", "payment_method", "deal_type", "user_role",
    ]:
        sa.Enum(name=enum).drop(op.get_bind(), checkfirst=True)
