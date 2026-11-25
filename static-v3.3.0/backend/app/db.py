import os
from pathlib import Path

from sqlalchemy import create_engine


snapshot = Path(os.environ.get("COURSE_SNAPSHOT", "/data/catalog.sqlite"))
engine = create_engine(
    f"sqlite:///{snapshot.resolve().as_uri()}?mode=ro&uri=true",
    pool_pre_ping=True,
)
