"""
SQLAlchemy ORM models for the fashion news assistant.

Article — stores individual fetched and filtered news articles.
Digest — stores daily pre-built digest cache.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, Integer, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Article(Base):
    """
    Represents a single news article fetched and filtered by the pipeline.
    """
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Базові поля — приходять із SearchService
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(200))
    published_at: Mapped[str] = mapped_column(String(100))  # ISO string
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI-поля — заповнюються після ArticleFilterService
    relevance: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)   # HIGH/MEDIUM/LOW
    include_in_digest: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)    # HIGH/MEDIUM/LOW
    article_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # trend/news/etc
    competitor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Службове
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Digest(Base):
    """
    Represents a daily digest — cached output of the full pipeline.
    """
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    digest_date: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # "2025-04-16"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
