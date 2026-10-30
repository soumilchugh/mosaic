"""add session and DeepAgents thread mapping

Revision ID: 20261030_0002
Revises: 20261029_0001
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261030_0002"
down_revision: str | None = "20261029_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("agent_task_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="created", nullable=False),
        sa.Column("depth", sa.String(length=30), server_default="standard", nullable=False),
        sa.Column("strategy", sa.String(length=30), server_default="hybrid", nullable=False),
        sa.Column("output_format", sa.String(length=30), server_default="report", nullable=False),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('created', 'planning', 'awaiting_intervention', 'researching', "
            "'writing', 'editing', 'completed', 'failed', 'cancelled')",
            name=op.f("ck_research_runs_status"),
        ),
        sa.CheckConstraint(
            "depth IN ('quick', 'standard', 'deep')",
            name=op.f("ck_research_runs_depth"),
        ),
        sa.CheckConstraint(
            "strategy IN ('breadth_first', 'depth_first', 'hybrid')",
            name=op.f("ck_research_runs_strategy"),
        ),
        sa.CheckConstraint(
            "output_format IN ('markdown', 'report', 'deck_later')",
            name=op.f("ck_research_runs_output_format"),
        ),
        sa.ForeignKeyConstraint(
            ["agent_task_id"],
            ["agent_tasks.id"],
            name=op.f("fk_research_runs_agent_task_id_agent_tasks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_research_runs_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_research_runs_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_research_runs_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_runs")),
        sa.UniqueConstraint("agent_task_id", name=op.f("uq_research_runs_agent_task_id")),
    )
    op.create_index(
        op.f("ix_research_runs_conversation_id"),
        "research_runs",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_research_runs_project_id"), "research_runs", ["project_id"], unique=False
    )

    op.add_column("messages", sa.Column("research_run_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_messages_research_run_id_research_runs"),
        "messages",
        "research_runs",
        ["research_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("product_events", sa.Column("research_run_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_product_events_research_run_id_research_runs"),
        "product_events",
        "research_runs",
        ["research_run_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        op.f("ck_deepagents_threads_owner"), "deepagents_threads", type_="check"
    )
    op.add_column("deepagents_threads", sa.Column("research_run_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_deepagents_threads_research_run_id_research_runs"),
        "deepagents_threads",
        "research_runs",
        ["research_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        op.f("ck_deepagents_threads_owner"),
        "deepagents_threads",
        "conversation_id IS NOT NULL OR agent_task_id IS NOT NULL OR research_run_id IS NOT NULL",
    )
    op.create_index(
        "uq_deepagents_threads_conversation_default",
        "deepagents_threads",
        ["conversation_id"],
        unique=True,
        postgresql_where=sa.text("agent_task_id IS NULL AND research_run_id IS NULL"),
    )
    op.create_index(
        "uq_deepagents_threads_research_run",
        "deepagents_threads",
        ["research_run_id"],
        unique=True,
        postgresql_where=sa.text("research_run_id IS NOT NULL"),
    )

    op.create_table(
        "intervention_requests",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("agent_task_id", sa.Uuid(), nullable=True),
        sa.Column("research_run_id", sa.Uuid(), nullable=True),
        sa.Column("deepagents_thread_id", sa.Uuid(), nullable=False),
        sa.Column("checkpoint_id", sa.String(length=500), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column(
            "request_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "agent_task_id IS NOT NULL OR research_run_id IS NOT NULL",
            name=op.f("ck_intervention_requests_owner"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'edited', 'rejected', 'expired', 'resolved')",
            name=op.f("ck_intervention_requests_status"),
        ),
        sa.CheckConstraint(
            "type IN ('topic_approval', 'tool_approval', 'memory_write', "
            "'filesystem_write', 'export_approval')",
            name=op.f("ck_intervention_requests_type"),
        ),
        sa.ForeignKeyConstraint(
            ["agent_task_id"],
            ["agent_tasks.id"],
            name=op.f("fk_intervention_requests_agent_task_id_agent_tasks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_intervention_requests_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deepagents_thread_id"],
            ["deepagents_threads.id"],
            name=op.f("fk_intervention_requests_deepagents_thread_id_deepagents_threads"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_intervention_requests_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_runs.id"],
            name=op.f("fk_intervention_requests_research_run_id_research_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intervention_requests")),
        sa.UniqueConstraint(
            "deepagents_thread_id",
            "checkpoint_id",
            name=op.f("uq_intervention_requests_deepagents_thread_id"),
        ),
    )
    op.create_index(
        op.f("ix_intervention_requests_project_id"),
        "intervention_requests",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_intervention_requests_project_id"), table_name="intervention_requests")
    op.drop_table("intervention_requests")
    op.drop_index("uq_deepagents_threads_research_run", table_name="deepagents_threads")
    op.drop_index("uq_deepagents_threads_conversation_default", table_name="deepagents_threads")
    op.drop_constraint(
        op.f("ck_deepagents_threads_owner"), "deepagents_threads", type_="check"
    )
    op.drop_constraint(
        op.f("fk_deepagents_threads_research_run_id_research_runs"),
        "deepagents_threads",
        type_="foreignkey",
    )
    op.drop_column("deepagents_threads", "research_run_id")
    op.create_check_constraint(
        op.f("ck_deepagents_threads_owner"),
        "deepagents_threads",
        "conversation_id IS NOT NULL OR agent_task_id IS NOT NULL",
    )
    op.drop_constraint(
        op.f("fk_product_events_research_run_id_research_runs"),
        "product_events",
        type_="foreignkey",
    )
    op.drop_column("product_events", "research_run_id")
    op.drop_constraint(
        op.f("fk_messages_research_run_id_research_runs"), "messages", type_="foreignkey"
    )
    op.drop_column("messages", "research_run_id")
    op.drop_index(op.f("ix_research_runs_project_id"), table_name="research_runs")
    op.drop_index(op.f("ix_research_runs_conversation_id"), table_name="research_runs")
    op.drop_table("research_runs")
