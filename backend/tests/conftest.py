"""Test configuration.

The tests must not need Postgres. Setting DATABASE_URL before the app is
imported points the module-level engine at SQLite instead.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-not-used-in-production")
