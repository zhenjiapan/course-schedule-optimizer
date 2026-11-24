import os
from sqlalchemy import create_engine

engine = create_engine(
    os.environ.get("DATABASE_URL", "postgresql+psycopg://planner:planner@127.0.0.1:55432/planner"),
    pool_pre_ping=True, pool_size=5, max_overflow=2, pool_timeout=5,
)
