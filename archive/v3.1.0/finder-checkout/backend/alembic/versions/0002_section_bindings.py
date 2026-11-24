from alembic import op

revision = "0002_section_bindings"
down_revision = "0001_catalog"


def upgrade():
    op.execute("CREATE TABLE IF NOT EXISTS section_bindings (course_code TEXT NOT NULL, term TEXT NOT NULL, lecture_section TEXT NOT NULL, tutorial_section TEXT NOT NULL, verified_at TEXT NOT NULL, PRIMARY KEY(course_code,term,lecture_section,tutorial_section))")


def downgrade():
    op.drop_table("section_bindings")
