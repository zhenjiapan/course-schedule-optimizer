"""Optional authoritative teaching dates, including makeup classes."""
from alembic import op

revision = "0003_meeting_occurrences"
down_revision = "0002_section_bindings"


def upgrade():
    op.execute("""
        CREATE TABLE meeting_occurrence_overrides (
            meeting_id BIGINT PRIMARY KEY REFERENCES meetings(id) ON DELETE CASCADE,
            occurrences DATE[] NOT NULL CHECK (array_position(occurrences, NULL) IS NULL)
        )
    """)


def downgrade():
    op.drop_table("meeting_occurrence_overrides")
