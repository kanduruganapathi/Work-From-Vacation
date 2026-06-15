"""Pytest setup: use an isolated database so tests don't interfere with a
running dev server (which uses the default SQLite file)."""

import os

# Must be set before any app module imports settings / creates the engine.
os.environ["DATABASE_URL"] = "sqlite:///./test_wfv.db"
