"""Create sessions, session_turns, jobs, and designs tables.

Revision ID: 0001_create_sessions_jobs_designs
Revises: None
Create Date: 2026-06-02 10:30:00
"""
from alembic import op


revision = "0001_create_sessions_jobs_designs"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id text PRIMARY KEY,
            user_id text,
            title text,
            status text NOT NULL DEFAULT 'active',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT sessions_status_check
                CHECK (status IN ('active', 'closed', 'archived'))
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id text PRIMARY KEY,
            session_id text NOT NULL,
            kind text NOT NULL,
            status text NOT NULL DEFAULT 'queued',
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            result jsonb,
            error jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            started_at timestamptz,
            completed_at timestamptz,
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT jobs_session_id_fkey
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            CONSTRAINT jobs_status_check
                CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled'))
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS designs (
            id text PRIMARY KEY,
            session_id text NOT NULL,
            job_id text NOT NULL,
            status text NOT NULL DEFAULT 'draft',
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            result jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT designs_session_id_fkey
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            CONSTRAINT designs_job_id_fkey
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            CONSTRAINT designs_status_check
                CHECK (status IN ('draft', 'ready', 'archived'))
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS session_turns (
            id text PRIMARY KEY,
            session_id text NOT NULL,
            turn_index integer NOT NULL,
            role text NOT NULL,
            content text NOT NULL,
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT session_turns_session_id_fkey
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            CONSTRAINT session_turns_turn_index_check
                CHECK (turn_index >= 0),
            CONSTRAINT session_turns_role_check
                CHECK (role IN ('user', 'assistant', 'system', 'tool'))
        )
        """
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_session_turns_session_turn_index "
        "ON session_turns (session_id, turn_index)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_session_turns_session_id_created_at "
        "ON session_turns (session_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sessions_status_created_at "
        "ON sessions (status, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sessions_user_id_created_at "
        "ON sessions (user_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_jobs_session_id_status_created_at "
        "ON jobs (session_id, status, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_jobs_status_created_at "
        "ON jobs (status, created_at)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_designs_job_id "
        "ON designs (job_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_designs_session_id_status_created_at "
        "ON designs (session_id, status, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_designs_session_id_status_created_at")
    op.execute("DROP INDEX IF EXISTS uq_designs_job_id")
    op.execute("DROP INDEX IF EXISTS ix_jobs_status_created_at")
    op.execute("DROP INDEX IF EXISTS ix_jobs_session_id_status_created_at")
    op.execute("DROP INDEX IF EXISTS ix_sessions_user_id_created_at")
    op.execute("DROP INDEX IF EXISTS ix_sessions_status_created_at")
    op.execute("DROP INDEX IF EXISTS ix_session_turns_session_id_created_at")
    op.execute("DROP INDEX IF EXISTS uq_session_turns_session_turn_index")
    op.execute("DROP TABLE IF EXISTS session_turns")
    op.execute("DROP TABLE IF EXISTS designs")
    op.execute("DROP TABLE IF EXISTS jobs")
    op.execute("DROP TABLE IF EXISTS sessions")
