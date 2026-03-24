"""
Book Intelligence Agent — FastAPI Application
A living knowledge library that grows smarter with every book.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config import get_settings
from database import init_db, get_db
from agent import BookIntelligenceAgent
from schemas import ProcessBookRequest, BatchProcessRequest, QueryRequest, QuickAddRequest
from models import Book, Category, Theme, Debate, IdeaIndex, MasterLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    logger.info("Initializing database...")
    try:
        init_db(retries=5, delay=3.0)
        logger.info("Database ready.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.error("The app will start but database endpoints will fail until DB is available.")
    yield


app = FastAPI(
    title="Book Intelligence Agent",
    description=(
        "A living knowledge library — give it book titles, and it builds "
        "structured summaries, categorised by theme, with cross-book synthesis, "
        "conflicting views surfaced, and its own commentary on what matters most."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── Health & Info ───────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "name": "Book Intelligence Agent",
        "version": "1.0.0",
        "description": "A living knowledge library for business, strategy, and psychology books.",
        "endpoints": {
            "POST /books": "Process a single book → Book Card",
            "POST /books/batch": "Process multiple books → Book Cards + Synthesis",
            "POST /master-log": "Generate/update the Master Log",
            "POST /query": "Query the library",
            "GET /library": "Get library stats",
            "GET /books": "List all books",
            "GET /books/{id}": "Get a specific book card",
            "GET /categories": "List all categories",
            "GET /themes": "List all themes",
            "GET /debates": "List all debates",
            "GET /ideas": "Search the idea index",
        },
    }


@app.get("/health", tags=["Info"])
def health():
    """Healthcheck endpoint — returns OK immediately so Railway doesn't kill the container."""
    try:
        from database import get_db_context
        with get_db_context() as db:
            book_count = db.query(Book).count()
            return {"status": "healthy", "books_in_library": book_count}
    except Exception:
        return {"status": "starting", "books_in_library": 0}


# ── MODE 1: Single Book Processing ─────────────────────────────────

@app.post("/books", tags=["Books"])
def process_book(request: ProcessBookRequest, db: Session = Depends(get_db)):
    """
    Process a single book and produce a full Book Card.
    The book is added to the library and all connections are updated.
    """
    try:
        agent = BookIntelligenceAgent(db)
        result = agent.process_book(
            book_title=request.book_title,
            depth=request.depth,
            user_context=request.user_context,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing book: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# ── MODE 2: Batch Processing ───────────────────────────────────────

@app.post("/books/batch", tags=["Books"])
def process_batch(request: BatchProcessRequest, db: Session = Depends(get_db)):
    """
    Process multiple books at once.
    Produces Book Cards for each + a Batch Synthesis showing connections.
    """
    try:
        agent = BookIntelligenceAgent(db)
        result = agent.process_batch(
            book_titles=request.book_titles,
            depth=request.depth,
            user_context=request.user_context,
        )
        return result
    except Exception as e:
        logger.error(f"Error in batch processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


# ── MODE 3: Master Log ─────────────────────────────────────────────

@app.post("/master-log", tags=["Master Log"])
def generate_master_log(db: Session = Depends(get_db)):
    """
    Generate or update the Master Log — the living library document.
    Synthesises all books, categories, themes, debates, and curator picks.
    """
    try:
        agent = BookIntelligenceAgent(db)
        result = agent.generate_master_log()
        return result
    except Exception as e:
        logger.error(f"Error generating master log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Master log generation failed: {str(e)}")


@app.get("/master-log", tags=["Master Log"])
def get_latest_master_log(db: Session = Depends(get_db)):
    """Get the latest version of the Master Log."""
    log = db.query(MasterLog).order_by(MasterLog.version.desc()).first()
    if not log:
        return {"status": "empty", "message": "No master log generated yet. POST /master-log to create one."}
    return {
        "version": log.version,
        "total_books": log.total_books,
        "last_updated": log.last_updated.isoformat(),
        "reading_priority_ranking": log.reading_priority_ranking,
        "curator_picks": log.curator_picks,
        "full_markdown": log.full_markdown,
    }


# ── MODE 4: Query Mode ─────────────────────────────────────────────

@app.post("/query", tags=["Query"])
def query_library(request: QueryRequest, db: Session = Depends(get_db)):
    """
    Query the library with any question.
    Gets synthesised answers drawing on all books, themes, and debates.
    """
    try:
        agent = BookIntelligenceAgent(db)
        result = agent.query_library(
            query=request.query,
            user_context=request.user_context,
        )
        return result
    except Exception as e:
        logger.error(f"Error querying library: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ── Library Browsing ────────────────────────────────────────────────

@app.get("/library", tags=["Library"])
def get_library_stats(db: Session = Depends(get_db)):
    """Get an overview of the current library state."""
    agent = BookIntelligenceAgent(db)
    return agent.get_library_stats()


@app.get("/books", tags=["Books"])
def list_books(
    category: str = Query(None, description="Filter by category name"),
    sort: str = Query("relevance", description="Sort by: relevance, title, year, added"),
    db: Session = Depends(get_db),
):
    """List all books in the library."""
    query = db.query(Book)

    if category:
        query = query.filter(Book.categories.any(Category.name.ilike(f"%{category}%")))

    if sort == "relevance":
        query = query.order_by(Book.relevance_score.desc())
    elif sort == "title":
        query = query.order_by(Book.title)
    elif sort == "year":
        query = query.order_by(Book.published_year.desc())
    elif sort == "added":
        query = query.order_by(Book.created_at.desc())

    books = query.all()
    return {
        "count": len(books),
        "books": [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "published_year": b.published_year,
                "relevance_score": b.relevance_score,
                "categories": [c.name for c in b.categories],
                "priority_rank": b.priority_rank,
            }
            for b in books
        ],
    }


@app.get("/books/{book_id}", tags=["Books"])
def get_book(book_id: int, db: Session = Depends(get_db)):
    """Get the full Book Card for a specific book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "published_year": book.published_year,
        "relevance_score": book.relevance_score,
        "relevance_rationale": book.relevance_rationale,
        "audience": book.audience,
        "categories": [c.name for c in book.categories],
        "core_argument": book.core_argument,
        "evidence_method": book.evidence_method,
        "ideas_worth_keeping": book.ideas_worth_keeping,
        "frameworks_tools": book.frameworks_tools,
        "what_gets_right": book.what_gets_right,
        "what_gets_wrong": book.what_gets_wrong,
        "curator_verdict": book.curator_verdict,
        "connections": book.connections,
        "book_card_markdown": book.book_card_markdown,
        "priority_rank": book.priority_rank,
        "created_at": book.created_at.isoformat(),
    }


@app.delete("/books/{book_id}", tags=["Books"])
def delete_book(book_id: int, db: Session = Depends(get_db)):
    """Remove a book from the library."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    title = book.title
    db.delete(book)
    db.commit()
    return {"status": "deleted", "title": title}


@app.get("/categories", tags=["Categories"])
def list_categories(db: Session = Depends(get_db)):
    """List all categories with their book counts and insights."""
    cats = db.query(Category).all()
    return {
        "count": len(cats),
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "book_count": len(c.books),
                "books": [b.title for b in c.books],
                "central_debate": c.central_debate,
                "best_entry_point": c.best_entry_point,
                "synthesis_insight": c.synthesis_insight,
            }
            for c in cats
        ],
    }


@app.get("/themes", tags=["Themes"])
def list_themes(db: Session = Depends(get_db)):
    """List all cross-book themes."""
    themes = db.query(Theme).all()
    return {
        "count": len(themes),
        "themes": [
            {
                "id": t.id,
                "name": t.name,
                "books": [b.title for b in t.books],
                "consensus_view": t.consensus_view,
                "dissenting_view": t.dissenting_view,
                "curator_synthesis": t.curator_synthesis,
            }
            for t in themes
        ],
    }


@app.get("/debates", tags=["Debates"])
def list_debates(db: Session = Depends(get_db)):
    """List all intellectual debates and tensions surfaced across books."""
    debates = db.query(Debate).all()
    return {
        "count": len(debates),
        "debates": [
            {
                "id": d.id,
                "question": d.question,
                "side_a": d.side_a_position,
                "side_a_books": d.side_a_books,
                "side_b": d.side_b_position,
                "side_b_books": d.side_b_books,
                "curator_position": d.curator_position,
                "resolution_path": d.resolution_path,
            }
            for d in debates
        ],
    }


@app.get("/ideas", tags=["Idea Index"])
def search_ideas(
    q: str = Query(None, description="Search term for concept names"),
    db: Session = Depends(get_db),
):
    """Search the idea index — named concepts, frameworks, and models."""
    query = db.query(IdeaIndex)
    if q:
        query = query.filter(IdeaIndex.concept_name.ilike(f"%{q}%"))
    ideas = query.all()
    return {
        "count": len(ideas),
        "ideas": [
            {
                "id": i.id,
                "concept_name": i.concept_name,
                "book": i.book.title if i.book else None,
                "definition": i.definition,
                "related_concepts": i.related_concepts,
            }
            for i in ideas
        ],
    }


# ── Quick Add (lightweight entry) ──────────────────────────────────

@app.post("/books/quick-add", tags=["Books"])
def quick_add_book(request: QuickAddRequest, db: Session = Depends(get_db)):
    """
    Quick-add a book with minimal info (no Claude processing).
    Useful for rapidly expanding the library with abbreviated entries.
    """
    book = Book(
        title=request.title,
        author=request.author,
        published_year=request.year,
        depth="QUICK",
        core_argument=request.core_idea,
        curator_verdict=f"Worth reading: {request.worth_reading}. Best idea: {request.best_idea}",
        connections={"connects_to": request.connects_to},
    )

    cat = db.query(Category).filter(Category.name.ilike(f"%{request.category}%")).first()
    if not cat:
        slug = request.category.lower().replace(" & ", "-and-").replace(" ", "-")
        cat = Category(name=request.category, slug=slug)
        db.add(cat)
        db.flush()
    book.categories.append(cat)

    db.add(book)
    db.commit()

    return {
        "status": "quick_added",
        "book_id": book.id,
        "title": book.title,
        "category": cat.name,
    }
