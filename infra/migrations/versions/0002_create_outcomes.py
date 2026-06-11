"""Create outcomes table for Phase 5 feedback capture.

Revision ID: 0002_outcomes
Revises: 0001_app_tables
Create Date: 2026-06-07 09:00:00
"""
from alembic import op


revision = "0002_outcomes"
down_revision = "0001_app_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS outcomes (
            id text PRIMARY KEY,
            design_id text NOT NULL,
            user_id text NOT NULL,
            model_version text NOT NULL,
            outcome_label text NOT NULL,
            construct_validated boolean,
            sequencing_result text,
            expression_result text,
            functional_result text,
            training_consent boolean NOT NULL DEFAULT false,
            provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
            report jsonb NOT NULL,
            derived_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT outcomes_design_id_fkey
                FOREIGN KEY (design_id) REFERENCES designs(id) ON DELETE CASCADE,
            CONSTRAINT outcomes_label_check
                CHECK (outcome_label IN ('positive', 'negative', 'ambiguous'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_outcomes_design_id_created_at ON outcomes (design_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_outcomes_user_id_created_at ON outcomes (user_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_outcomes_derived_at_created_at ON outcomes (derived_at, created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_outcomes_derived_at_created_at")
    op.execute("DROP INDEX IF EXISTS ix_outcomes_user_id_created_at")
    op.execute("DROP INDEX IF EXISTS ix_outcomes_design_id_created_at")
    op.execute("DROP TABLE IF EXISTS outcomes")
