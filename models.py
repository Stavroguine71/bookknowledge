"""
Database models for the Book Intelligence Agent.
PostgreSQL schema for the living knowledge library.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey,
    Table, Boolean, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

# ── Association Tables ──────────────────────────────────────────────

book_categories = Table(
    "book_categories", Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    Column("is_primary", Boolean, default=False),
)

book_themes = Table(
    "book_themes", Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("theme_id", Integer, ForeignKey("themes.id", ondelete="CASCADE"), primary_key=True),
)

debate_books = Table(
    "debate_books", Base.metadata,
    Column("debate_id", Integer, ForeignKey("debates.id", ondelete="CASCADE"), primary_key=True),
    Column("book_id", Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("side", String(10)),  # 'A' or 'B'
)


# ── Core Models ─────────────────────────────────────────────────────

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    author = Column(String(500), nullable=False)
    published_year = Column(Integer)
    reading_time_hours = Column(Float)
    relevance_score = Column(Integer)  # 1-5
    relevance_rationale = Column(Text)
    audience = Column(Text)
    depth = Column(String(20), default="FULL")  # FULL, CORE, QUICK

    # Book Card sections (stored as structured text)
    core_argument = Column(Text)
    evidence_method = Column(Text)
    ideas_worth_keeping = Column(JSONB)  # [{name, explanation, practical}]
    frameworks_tools = Column(JSONB)     # [{name, what_it_does, when_to_use, limitation}]
    what_gets_right = Column(Text)
    what_gets_wrong = Column(Text)
    curator_verdict = Column(Text)
    connections = Column(JSONB)          # {builds_on:[], challenges:[], pairs_with:[], etc.}

    # Full rendered card (markdown)
    book_card_markdown = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    priority_rank = Column(Integer)
    priority_rationale = Column(Text)

    # Relationships
    categories = relationship("Category", secondary=book_categories, back_populates="books")
    themes = relationship("Theme", secondary=book_themes, back_populates="books")

    # Full-text search index
    __table_args__ = (
        Index("idx_books_title_author", "title", "author"),
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    landmark_books = Column(Text)  # Comma-separated reference titles

    # Category file content (updated with each book addition)
    central_debate = Column(Text)
    best_entry_point = Column(Text)
    most_underrated = Column(Text)
    most_overrated = Column(Text)
    key_tensions = Column(Text)
    synthesis_insight = Column(Text)
    category_file_markdown = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    books = relationship("Book", secondary=book_categories, back_populates="categories")


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(300), nullable=False, unique=True)
    consensus_view = Column(Text)
    dissenting_view = Column(Text)
    curator_synthesis = Column(Text)
    most_useful_book = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    books = relationship("Book", secondary=book_themes, back_populates="themes")


class Debate(Base):
    __tablename__ = "debates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    side_a_position = Column(Text)
    side_a_books = Column(JSONB)  # [{title, author}]
    side_b_position = Column(Text)
    side_b_books = Column(JSONB)  # [{title, author}]
    curator_position = Column(Text)
    resolution_path = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IdeaIndex(Base):
    """Searchable index of named concepts, frameworks, and models across all books."""
    __tablename__ = "idea_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_name = Column(String(300), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"))
    definition = Column(Text)
    related_concepts = Column(JSONB)  # [concept_name strings]

    created_at = Column(DateTime, default=datetime.utcnow)

    book = relationship("Book")

    __table_args__ = (
        Index("idx_idea_concept", "concept_name"),
    )


class MasterLog(Base):
    """The living library document — regenerated/updated with each addition."""
    __tablename__ = "master_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, nullable=False)
    total_books = Column(Integer, default=0)
    categories_represented = Column(JSONB)  # [category names]
    date_range = Column(String(100))
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Full rendered sections
    library_overview = Column(Text)
    reading_priority_ranking = Column(JSONB)  # [{rank, title, rationale}]
    knowledge_map = Column(Text)  # Category files combined
    cross_book_themes = Column(Text)
    idea_index_summary = Column(Text)
    debates_tensions = Column(Text)
    curator_picks = Column(JSONB)  # {most_practical, most_intellectual, most_underrated, ...}
    library_gaps = Column(Text)

    # Full rendered master log markdown
    full_markdown = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


class ProcessingLog(Base):
    """Track what was processed and when."""
    __tablename__ = "processing_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(50))  # book_card, batch, master_log_update, query
    input_data = Column(JSONB)
    output_summary = Column(Text)
    books_processed = Column(JSONB)  # [book_ids]
    created_at = Column(DateTime, default=datetime.utcnow)
