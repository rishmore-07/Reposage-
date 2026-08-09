"""
app/db/base.py

SQLAlchemy declarative base and shared metadata.

All ORM models must import and inherit from Base defined here.
This ensures Alembic can discover all tables via metadata.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, MappedColumn


class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy declarative base.

    All ORM models inherit from this class. By importing all models
    in alembic/env.py (or app/db/init_db.py), Alembic can auto-detect
    table additions and removals via metadata comparison.
    """

    # Declarative base provides:
    # - metadata: MetaData (used by Alembic)
    # - registry: maps Python classes to SQL tables
    pass
