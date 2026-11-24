from pathlib import Path
from alembic import op

revision = "0001_catalog"
down_revision = None

def upgrade():
    sql = Path(__file__).parents[2].joinpath("schema.sql").read_text()
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)

def downgrade():
    for table in ("collection_runs", "meeting_instructors", "instructors", "meeting_days",
                  "meetings", "sections", "course_attributes", "course_components", "courses", "sources"):
        op.drop_table(table)
