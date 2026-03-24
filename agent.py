"""
Core agent logic — interfaces with Claude API and orchestrates
the four processing modes: Book Card, Batch, Master Log, Query.
"""

import json
import logging
from typing import Optional

import anthropic
from sqlalchemy.orm import Session

from config import get_settings
from models import Book, Category, Theme, Debate, IdeaIndex, MasterLog, ProcessingLog
from prompts import (
    SYSTEM_PROMPT, BOOK_CARD_PROMPT, BATCH_SYNTHESIS_PROMPT,
    MASTER_LOG_PROMPT, QUERY_PROMPT, CATEGORY_UPDATE_PROMPT,
    format_book_card_markdown,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class BookIntelligenceAgent:
    """The brain of the Book Intelligence Agent."""

    def __init__(self, db: Session):
        self.db = db
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY", "") or settings.anthropic_api_key
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Add it to your Railway environment variables."
            )
        self.client = anthropic.Anthropic(api_key=api_key)

    # ── Claude API Call ─────────────────────────────────────────────

    def _call_claude(self, user_prompt: str, max_tokens: int = None) -> dict:
        """Send a prompt to Claude and parse the JSON response."""
        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens or settings.claude_max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines[1:] if not l.strip() == "```"]
            raw_text = "\n".join(lines)

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Raw response: {raw_text[:500]}")
            raise ValueError(f"Claude returned invalid JSON: {e}")

    # ── Library State Helpers ───────────────────────────────────────

    def _get_existing_library_summary(self) -> str:
        """Build a summary of all books currently in the library."""
        books = self.db.query(Book).all()
        if not books:
            return "EMPTY — this is the first book being added."

        lines = []
        for b in books:
            cats = ", ".join([c.name for c in b.categories]) if b.categories else "Uncategorized"
            lines.append(
                f"- {b.title} by {b.author} ({b.published_year}) "
                f"[{cats}] — Relevance: {b.relevance_score}/5"
            )
        return "\n".join(lines)

    def _get_all_books_summary(self) -> str:
        """Detailed summary of all books for master log generation."""
        books = self.db.query(Book).all()
        summaries = []
        for b in books:
            cats = ", ".join([c.name for c in b.categories]) if b.categories else "Uncategorized"
            summaries.append(
                f"TITLE: {b.title}\n"
                f"AUTHOR: {b.author}\n"
                f"YEAR: {b.published_year}\n"
                f"CATEGORIES: {cats}\n"
                f"RELEVANCE: {b.relevance_score}/5\n"
                f"CORE ARGUMENT: {b.core_argument}\n"
                f"CURATOR VERDICT: {b.curator_verdict}\n"
                f"---"
            )
        return "\n".join(summaries) if summaries else "No books yet."

    def _get_categories_summary(self) -> str:
        cats = self.db.query(Category).all()
        lines = []
        for c in cats:
            book_titles = [b.title for b in c.books]
            lines.append(f"{c.name}: {len(book_titles)} books — {', '.join(book_titles)}")
        return "\n".join(lines) if lines else "No categories yet."

    def _get_themes_summary(self) -> str:
        themes = self.db.query(Theme).all()
        lines = []
        for t in themes:
            book_titles = [b.title for b in t.books]
            lines.append(f"{t.name}: {', '.join(book_titles)}")
        return "\n".join(lines) if lines else "No themes yet."

    def _get_debates_summary(self) -> str:
        debates = self.db.query(Debate).all()
        lines = []
        for d in debates:
            lines.append(f"DEBATE: {d.question}\nSIDE A: {d.side_a_position}\nSIDE B: {d.side_b_position}")
        return "\n".join(lines) if lines else "No debates yet."

    def _get_ideas_summary(self) -> str:
        ideas = self.db.query(IdeaIndex).all()
        lines = []
        for i in ideas:
            book_title = i.book.title if i.book else "Unknown"
            lines.append(f"{i.concept_name} — {book_title} — {i.definition}")
        return "\n".join(lines) if lines else "No ideas indexed yet."

    def _get_full_library_state(self) -> str:
        """Complete library state for query mode."""
        return (
            f"=== BOOKS ===\n{self._get_all_books_summary()}\n\n"
            f"=== CATEGORIES ===\n{self._get_categories_summary()}\n\n"
            f"=== THEMES ===\n{self._get_themes_summary()}\n\n"
            f"=== DEBATES ===\n{self._get_debates_summary()}\n\n"
            f"=== IDEA INDEX ===\n{self._get_ideas_summary()}"
        )

    # ── Category Management ─────────────────────────────────────────

    def _get_or_create_category(self, name: str) -> Category:
        """Find or create a category by name."""
        slug = name.lower().replace(" & ", "-and-").replace(" ", "-")
        cat = self.db.query(Category).filter(Category.slug == slug).first()
        if not cat:
            cat = Category(name=name, slug=slug)
            self.db.add(cat)
            self.db.flush()
        return cat

    def _update_category_file(self, category: Category):
        """Re-generate a category file after a book is added."""
        if not category.books:
            return

        books_desc = "\n".join([
            f"- {b.title} by {b.author}: {b.core_argument}"
            for b in category.books
        ])

        prompt = CATEGORY_UPDATE_PROMPT.format(
            category_name=category.name,
            books_in_category=books_desc,
        )

        try:
            data = self._call_claude(prompt, max_tokens=2048)
            category.central_debate = data.get("central_debate", "")
            category.best_entry_point = data.get("best_entry_point", "")
            category.most_underrated = data.get("most_underrated", "")
            category.most_overrated = data.get("most_overrated", "")
            category.key_tensions = data.get("key_tensions", "")
            category.synthesis_insight = data.get("synthesis_insight", "")
        except Exception as e:
            logger.warning(f"Failed to update category file for {category.name}: {e}")

    # ── MODE 1: Single Book Processing ──────────────────────────────

    def process_book(
        self,
        book_title: str,
        depth: str = "FULL",
        user_context: str = "Knowledge worker building a personal library",
    ) -> dict:
        """Process a single book and produce a Book Card."""

        # Check if already in library
        existing = self.db.query(Book).filter(
            Book.title.ilike(f"%{book_title}%")
        ).first()
        if existing:
            return {
                "status": "already_exists",
                "book_id": existing.id,
                "title": existing.title,
                "book_card_markdown": existing.book_card_markdown,
            }

        existing_library = self._get_existing_library_summary()

        prompt = BOOK_CARD_PROMPT.format(
            book_title=book_title,
            depth=depth,
            user_context=user_context,
            existing_library=existing_library,
        )

        data = self._call_claude(prompt, max_tokens=settings.claude_max_tokens)

        # Create the Book record
        book = Book(
            title=data.get("title", book_title),
            author=data.get("author", "Unknown"),
            published_year=data.get("published_year"),
            reading_time_hours=data.get("reading_time_hours"),
            relevance_score=data.get("relevance_score", 3),
            relevance_rationale=data.get("relevance_rationale", ""),
            audience=data.get("audience", ""),
            depth=depth,
            core_argument=data.get("core_argument", ""),
            evidence_method=data.get("evidence_method", ""),
            ideas_worth_keeping=data.get("ideas_worth_keeping", []),
            frameworks_tools=data.get("frameworks_tools", []),
            what_gets_right=data.get("what_gets_right", ""),
            what_gets_wrong=data.get("what_gets_wrong", ""),
            curator_verdict=data.get("curator_verdict", ""),
            connections=data.get("connections", {}),
        )

        # Generate and store the markdown card
        book.book_card_markdown = format_book_card_markdown(data)

        self.db.add(book)
        self.db.flush()

        # Assign categories
        for cat_name in data.get("categories", []):
            cat = self._get_or_create_category(cat_name)
            book.categories.append(cat)

        # Create idea index entries
        for entry in data.get("idea_index_entries", []):
            idea = IdeaIndex(
                concept_name=entry.get("concept_name", ""),
                book_id=book.id,
                definition=entry.get("definition", ""),
                related_concepts=entry.get("related_concepts", []),
            )
            self.db.add(idea)

        # Create or update themes
        for theme_name in data.get("themes", []):
            theme = self.db.query(Theme).filter(Theme.name == theme_name).first()
            if not theme:
                theme = Theme(name=theme_name)
                self.db.add(theme)
                self.db.flush()
            book.themes.append(theme)

        self.db.flush()

        # Update category files for all assigned categories
        for cat in book.categories:
            self._update_category_file(cat)

        # Log the processing
        log = ProcessingLog(
            action="book_card",
            input_data={"title": book_title, "depth": depth},
            output_summary=f"Processed: {book.title} by {book.author}",
            books_processed=[book.id],
        )
        self.db.add(log)
        self.db.commit()

        return {
            "status": "created",
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "relevance_score": book.relevance_score,
            "categories": [c.name for c in book.categories],
            "book_card_markdown": book.book_card_markdown,
            "data": data,
        }

    # ── MODE 2: Batch Processing ────────────────────────────────────

    def process_batch(
        self,
        book_titles: list[str],
        depth: str = "FULL",
        user_context: str = "Knowledge worker building a personal library",
    ) -> dict:
        """Process multiple books and produce Book Cards + Batch Synthesis."""

        if len(book_titles) > settings.max_books_per_batch:
            return {
                "status": "error",
                "message": f"Maximum {settings.max_books_per_batch} books per batch.",
            }

        results = []
        for title in book_titles:
            try:
                result = self.process_book(title, depth=depth, user_context=user_context)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process '{title}': {e}")
                results.append({"status": "error", "title": title, "error": str(e)})

        # Generate batch synthesis
        processed_books = [r for r in results if r.get("status") == "created"]
        book_summaries = "\n\n".join([
            f"TITLE: {r['title']}\nRELEVANCE: {r.get('relevance_score', '?')}/5\n"
            f"CATEGORIES: {', '.join(r.get('categories', []))}"
            for r in processed_books
        ])

        synthesis = {}
        if len(processed_books) >= 2:
            try:
                synthesis_prompt = BATCH_SYNTHESIS_PROMPT.format(
                    book_summaries=book_summaries,
                    existing_library=self._get_existing_library_summary(),
                )
                synthesis = self._call_claude(synthesis_prompt, max_tokens=4096)

                # Store new debates from synthesis
                for debate_data in synthesis.get("new_debates", []):
                    debate = Debate(
                        question=debate_data.get("question", ""),
                        side_a_position=debate_data.get("side_a_position", ""),
                        side_a_books=debate_data.get("side_a_books", []),
                        side_b_position=debate_data.get("side_b_position", ""),
                        side_b_books=debate_data.get("side_b_books", []),
                        curator_position=debate_data.get("curator_position", ""),
                        resolution_path=debate_data.get("resolution_path", ""),
                    )
                    self.db.add(debate)

                # Store new themes from synthesis
                for theme_data in synthesis.get("new_themes", []):
                    existing_theme = self.db.query(Theme).filter(
                        Theme.name == theme_data.get("name")
                    ).first()
                    if existing_theme:
                        existing_theme.consensus_view = theme_data.get("consensus_view", "")
                        existing_theme.dissenting_view = theme_data.get("dissenting_view", "")
                        existing_theme.curator_synthesis = theme_data.get("curator_synthesis", "")
                        existing_theme.most_useful_book = theme_data.get("most_useful_book", "")
                    else:
                        theme = Theme(
                            name=theme_data.get("name", ""),
                            consensus_view=theme_data.get("consensus_view", ""),
                            dissenting_view=theme_data.get("dissenting_view", ""),
                            curator_synthesis=theme_data.get("curator_synthesis", ""),
                            most_useful_book=theme_data.get("most_useful_book", ""),
                        )
                        self.db.add(theme)

                self.db.commit()
            except Exception as e:
                logger.error(f"Failed to generate batch synthesis: {e}")

        # Log
        log = ProcessingLog(
            action="batch",
            input_data={"titles": book_titles, "depth": depth},
            output_summary=f"Batch processed {len(processed_books)} of {len(book_titles)} books",
            books_processed=[r.get("book_id") for r in processed_books if r.get("book_id")],
        )
        self.db.add(log)
        self.db.commit()

        return {
            "status": "completed",
            "books_processed": len(processed_books),
            "books_skipped": len(book_titles) - len(processed_books),
            "results": results,
            "batch_synthesis": synthesis,
        }

    # ── MODE 3: Master Log ──────────────────────────────────────────

    def generate_master_log(self) -> dict:
        """Generate or update the Master Log."""

        book_count = self.db.query(Book).count()
        if book_count == 0:
            return {"status": "empty", "message": "No books in library yet."}

        prompt = MASTER_LOG_PROMPT.format(
            all_books_summary=self._get_all_books_summary(),
            categories_summary=self._get_categories_summary(),
            themes_summary=self._get_themes_summary(),
            debates_summary=self._get_debates_summary(),
            ideas_summary=self._get_ideas_summary(),
        )

        data = self._call_claude(prompt, max_tokens=settings.claude_max_tokens)

        # Get current version
        latest = self.db.query(MasterLog).order_by(MasterLog.version.desc()).first()
        new_version = (latest.version + 1) if latest else 1

        master_log = MasterLog(
            version=new_version,
            total_books=book_count,
            categories_represented=data.get("library_overview", {}).get("categories_represented", []),
            date_range=data.get("library_overview", {}).get("date_range", ""),
            reading_priority_ranking=data.get("library_overview", {}).get("reading_priority_ranking", []),
            library_overview=json.dumps(data.get("library_overview", {}), indent=2),
            knowledge_map=json.dumps(data.get("category_files", []), indent=2),
            cross_book_themes=json.dumps(data.get("cross_book_themes", []), indent=2),
            debates_tensions=json.dumps(data.get("debates_tensions", []), indent=2),
            curator_picks=data.get("curator_picks", {}),
            library_gaps=data.get("library_gaps", ""),
            full_markdown=self._render_master_log_markdown(data),
        )

        self.db.add(master_log)

        # Update priority rankings on books
        for ranking in data.get("library_overview", {}).get("reading_priority_ranking", []):
            book = self.db.query(Book).filter(
                Book.title.ilike(f"%{ranking.get('title', '')}%")
            ).first()
            if book:
                book.priority_rank = ranking.get("rank")
                book.priority_rationale = ranking.get("rationale", "")

        # Log
        log = ProcessingLog(
            action="master_log_update",
            input_data={"version": new_version},
            output_summary=f"Master Log v{new_version} generated with {book_count} books",
        )
        self.db.add(log)
        self.db.commit()

        return {
            "status": "generated",
            "version": new_version,
            "total_books": book_count,
            "master_log_markdown": master_log.full_markdown,
            "data": data,
        }

    def _render_master_log_markdown(self, data: dict) -> str:
        """Render the master log as markdown."""
        overview = data.get("library_overview", {})
        rankings = overview.get("reading_priority_ranking", [])
        ranking_lines = "\n".join([
            f"{r.get('rank', '?')}. **{r.get('title', '')}** — {r.get('rationale', '')}"
            for r in rankings
        ])

        category_files = data.get("category_files", [])
        cat_sections = ""
        for cf in category_files:
            cat_sections += f"""
### {cf.get('category_name', '')}
**Books:** {cf.get('book_count', 0)} | {', '.join(cf.get('book_titles', []))}

**Central debate:** {cf.get('central_debate', '')}
**Best entry point:** {cf.get('best_entry_point', '')}
**Most underrated:** {cf.get('most_underrated', '')}
**Most overrated:** {cf.get('most_overrated', '')}
**Key tensions:** {cf.get('key_tensions', '')}
**Synthesis insight:** {cf.get('synthesis_insight', '')}

---
"""

        themes = data.get("cross_book_themes", [])
        theme_sections = ""
        for t in themes:
            theme_sections += f"""
### {t.get('theme_name', '')}
**Books:** {', '.join(t.get('books', []))}
**Consensus:** {t.get('consensus_view', '')}
**Dissent:** {t.get('dissenting_view', '')}
**Curator synthesis:** {t.get('curator_synthesis', '')}
**Most useful book:** {t.get('most_useful_book', '')}

"""

        debates = data.get("debates_tensions", [])
        debate_sections = ""
        for d in debates:
            debate_sections += f"""
### {d.get('question', '')}
**Side A:** {d.get('side_a', '')}
**Side B:** {d.get('side_b', '')}
**Curator position:** {d.get('curator_position', '')}
**Resolution:** {d.get('resolution_path', '')}

"""

        picks = data.get("curator_picks", {})
        picks_section = ""
        for key, val in picks.items():
            label = key.replace("_", " ").title()
            if isinstance(val, dict):
                picks_section += f"**{label}:** {val.get('title', '')} — {val.get('reason', '')}\n\n"

        return f"""# MASTER LOG — THE LIVING LIBRARY

## Section 1 — Library Overview

**Books in library:** {overview.get('total_books', 0)}
**Categories:** {', '.join(overview.get('categories_represented', []))}
**Date range:** {overview.get('date_range', '')}

### Reading Priority Ranking

{ranking_lines}

---

## Section 2 — Knowledge Map by Category

{cat_sections}

## Section 3 — Cross-Book Themes

{theme_sections}

## Section 4 — Debates & Tensions

{debate_sections}

## Section 5 — The Curator's Picks

{picks_section}

## Section 6 — Gaps in the Library

{data.get('library_gaps', 'Not yet assessed.')}
"""

    # ── MODE 4: Query Mode ──────────────────────────────────────────

    def query_library(
        self,
        query: str,
        user_context: str = "Knowledge worker",
    ) -> dict:
        """Query the library and get synthesised answers."""

        book_count = self.db.query(Book).count()
        if book_count == 0:
            return {
                "status": "empty",
                "message": "No books in library yet. Add some books first.",
            }

        prompt = QUERY_PROMPT.format(
            query=query,
            user_context=user_context,
            library_state=self._get_full_library_state(),
        )

        data = self._call_claude(prompt, max_tokens=settings.claude_max_tokens)

        # Log
        log = ProcessingLog(
            action="query",
            input_data={"query": query, "context": user_context},
            output_summary=data.get("answer", "")[:200],
        )
        self.db.add(log)
        self.db.commit()

        return {
            "status": "answered",
            "query": query,
            **data,
        }

    # ── Library Stats ───────────────────────────────────────────────

    def get_library_stats(self) -> dict:
        """Get current library statistics."""
        book_count = self.db.query(Book).count()
        category_count = self.db.query(Category).count()
        theme_count = self.db.query(Theme).count()
        debate_count = self.db.query(Debate).count()
        idea_count = self.db.query(IdeaIndex).count()

        latest_log = self.db.query(MasterLog).order_by(MasterLog.version.desc()).first()

        top_books = (
            self.db.query(Book)
            .filter(Book.priority_rank.isnot(None))
            .order_by(Book.priority_rank)
            .limit(10)
            .all()
        )

        return {
            "total_books": book_count,
            "total_categories": category_count,
            "total_themes": theme_count,
            "total_debates": debate_count,
            "total_ideas_indexed": idea_count,
            "master_log_version": latest_log.version if latest_log else 0,
            "last_updated": latest_log.last_updated.isoformat() if latest_log else None,
            "top_books": [
                {"rank": b.priority_rank, "title": b.title, "author": b.author}
                for b in top_books
            ],
        }
