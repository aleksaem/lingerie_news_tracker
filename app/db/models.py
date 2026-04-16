"""
SQLAlchemy ORM models for the fashion news assistant.

Article — stores individual fetched and filtered news articles.
Digest — stores daily pre-built digest cache.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Article(Base):
    """
    Represents a single news article fetched and filtered by the pipeline.
    """
    __tablename__ = "articles"
    # TODO: add columns: id, url (unique), title, content, source,
    #       published_at, summary, why_it_matters, priority, tags, created_at


class Digest(Base):
    """
    Represents a daily digest — cached output of the full pipeline.
    """
    __tablename__ = "digests"
    # TODO: add columns: id, date (unique), text, created_at
