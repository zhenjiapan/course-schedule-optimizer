"""Serve the exported Next.js site after registering the API routes."""
import os

from starlette.staticfiles import StaticFiles

from .main import app

app.mount("/", StaticFiles(directory=os.environ.get("SITE_DIR", "/site"), html=True))
