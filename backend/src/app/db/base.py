"""Provide a Base compatible with SQLAlchemy 1.x and 2.x.

If SQLAlchemy >= 2.0 is installed, use DeclarativeBase. Otherwise fall back
to the classic declarative_base() factory for older versions.
"""
try:
    # SQLAlchemy 2.0+ style
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass
except Exception:
    # Fallback for SQLAlchemy 1.x
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()
