"""Persist asynchronous task snapshots."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260812_0002"
down_revision: Union[str, None] = "20260812_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "async_tasks" in inspector.get_table_names():
        return
    op.create_table(
        "async_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(80), nullable=False),
        sa.Column("task_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("current_agent", sa.String(200), nullable=False, server_default=""),
        sa.Column("step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at_text", sa.Text(), nullable=False),
        sa.Column("started_at_text", sa.Text(), nullable=False),
        sa.Column("completed_at_text", sa.Text(), nullable=False),
        sa.Column("updated_at_text", sa.Text(), nullable=False),
        sa.Column("elapsed_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("step_timings", sa.Text(), nullable=False),
        sa.Column("result_payload", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("metadata_payload", sa.Text(), nullable=False),
        sa.Column("request_payload", sa.Text(), nullable=False),
        sa.Column("events_payload", sa.Text(), nullable=False),
        sa.Column("retry_of", sa.String(80), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_async_tasks_task_id", "async_tasks", ["task_id"], unique=True)
    op.create_index("ix_async_tasks_task_type", "async_tasks", ["task_type"])
    op.create_index("ix_async_tasks_status", "async_tasks", ["status"])
    op.create_index("ix_async_tasks_retry_of", "async_tasks", ["retry_of"])


def downgrade() -> None:
    op.drop_table("async_tasks")
