"""Create app users and accepted trial records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_users_trials"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("oidc_issuer", sa.Text(), nullable=False),
        sa.Column("oidc_subject", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "oidc_issuer", "oidc_subject", name="uq_app_users_oidc_identity"
        ),
    )
    op.create_table(
        "trials",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("case_text", sa.Text(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("verdict", postgresql.JSONB(), nullable=False),
        sa.Column(
            "checks",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("first_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "char_length(btrim(case_text)) BETWEEN 5 AND 300",
            name="chk_trials_case_length",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(verdict) = 'object'", name="chk_trials_verdict_object"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(checks) = 'array'", name="chk_trials_checks_array"
        ),
        sa.CheckConstraint(
            "submitted_at <= accepted_at", name="chk_trials_submitted_before_acceptance"
        ),
        sa.CheckConstraint(
            "first_checked_at IS NULL OR first_checked_at >= submitted_at",
            name="chk_trials_first_check_after_submission",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR (first_checked_at IS NOT NULL "
            "AND completed_at >= first_checked_at)",
            name="chk_trials_completion_after_first_check",
        ),
    )
    op.create_index(
        "ix_trials_owner_accepted",
        "trials",
        ["owner_id", sa.text("accepted_at DESC")],
    )
    op.execute(
        """
        CREATE FUNCTION set_trials_updated_at()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_trials_updated_at
        BEFORE UPDATE ON trials
        FOR EACH ROW
        EXECUTE FUNCTION set_trials_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_trials_updated_at ON trials")
    op.execute("DROP FUNCTION IF EXISTS set_trials_updated_at()")
    op.drop_index("ix_trials_owner_accepted", table_name="trials")
    op.drop_table("trials")
    op.drop_table("app_users")
