"""Initial learning workflow schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260812_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learners",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("profile_type", sa.String(200), nullable=False),
        sa.Column("background", sa.Text(), nullable=False),
        sa.Column("characteristics", sa.Text(), nullable=False),
        sa.Column("learning_goal", sa.Text(), nullable=False),
        sa.Column("level", sa.String(40), nullable=False),
        sa.Column("recommended_domains", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("profile_id"),
    )
    op.create_index("ix_learners_profile_id", "learners", ["profile_id"], unique=True)
    _create_workflow_tables()


def _create_workflow_tables() -> None:
    op.create_table(
        "diagnosis_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(80), nullable=False),
        sa.Column("profile_id", sa.String(80), nullable=False),
        sa.Column("domain", sa.String(40), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(80), nullable=False),
        sa.Column("weak_points", sa.Text(), nullable=False),
        sa.Column("strong_points", sa.Text(), nullable=False),
        sa.Column("diagnosis_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for name in ("session_id", "profile_id", "domain"):
        op.create_index(f"ix_diagnosis_records_{name}", "diagnosis_records", [name])
    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(80), nullable=False),
        sa.Column("profile_id", sa.String(80), nullable=False),
        sa.Column("domain", sa.String(40), nullable=False),
        sa.Column("learning_goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("session_id"),
    )
    for name in ("session_id", "profile_id", "domain"):
        op.create_index(f"ix_agent_sessions_{name}", "agent_sessions", [name], unique=name == "session_id")
    _create_payload_table("agent_steps", [
        sa.Column("agent_name", sa.String(200), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_ids", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
    ])
    _create_payload_table("generated_resources", [
        sa.Column("personalized_lecture", sa.Text(), nullable=False),
        sa.Column("practical_guide", sa.Text(), nullable=False),
        sa.Column("graded_quiz", sa.Text(), nullable=False),
        sa.Column("case_task", sa.Text(), nullable=False),
    ])
    _create_payload_table("learning_reports", [
        sa.Column("report_markdown", sa.Text(), nullable=False),
        sa.Column("weak_points", sa.Text(), nullable=False),
        sa.Column("learning_path", sa.Text(), nullable=False),
        sa.Column("next_training_plan", sa.Text(), nullable=False),
        sa.Column("review_comments", sa.Text(), nullable=False),
    ])
    _create_payload_table("feedback_records", [
        sa.Column("feedback_score", sa.Integer(), nullable=False),
        sa.Column("self_feedback", sa.Text(), nullable=False),
        sa.Column("next_action", sa.String(100), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("updated_learning_path", sa.Text(), nullable=False),
    ])
    op.create_table(
        "learning_interactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("interaction_id", sa.String(80), nullable=False),
        sa.Column("session_id", sa.String(80), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.Text(), nullable=False),
        sa.Column("retrieval_mode", sa.String(80), nullable=False),
        sa.Column("knowledge_source", sa.String(100), nullable=False),
        sa.Column("generation_mode", sa.String(80), nullable=False),
        sa.Column("review_status", sa.String(100), nullable=False),
        sa.Column("next_action", sa.String(100), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("interaction_id"),
    )
    op.create_index("ix_learning_interactions_interaction_id", "learning_interactions", ["interaction_id"], unique=True)
    op.create_index("ix_learning_interactions_session_id", "learning_interactions", ["session_id"])


def _create_payload_table(name: str, columns: list[sa.Column]) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(80), nullable=False),
        *columns,
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(f"ix_{name}_session_id", name, ["session_id"])


def downgrade() -> None:
    for table in (
        "learning_interactions", "feedback_records", "learning_reports",
        "generated_resources", "agent_steps", "agent_sessions", "diagnosis_records", "learners",
    ):
        op.drop_table(table)
