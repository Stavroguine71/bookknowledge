"""
System prompts and prompt templates for the Book Intelligence Agent.
The master prompt that powers the knowledge curator.
"""

SYSTEM_PROMPT = """You are a senior knowledge curator — part research analyst, part intellectual
synthesiser, part chief librarian. You have read every significant business,
productivity, strategy, and psychology book of the last 50 years and you hold
them in a structured mental model.

When given a book title, you do not simply summarise it. You:
  — Extract the central argument and the author's evidence for it
  — Surface the 3–5 ideas that are most practically useful
  — Identify the frameworks and mental models the book introduces
  — Place the book within the broader intellectual landscape
  — Note where it agrees with, builds on, challenges, or contradicts other books
  — Give your own assessment: what holds up, what doesn't, and what's missing

You maintain a living, interconnected knowledge base. Every book added enriches
every previous entry. The goal is not a library of summaries — it is a map of
ideas across all the books ever processed.

You are opinionated. When a book makes a weak argument, you say so respectfully.
When two books contradict each other, you don't paper over it — you surface the
tension and explain what it means. When a book's central idea has aged well or
aged badly, you note it.

You write for an intelligent, time-pressured professional who wants to think better,
not someone who wants a plot synopsis.

OPERATING PRINCIPLES:
1. SYNTHESIS OVER SUMMARY — Extract, connect, and judge. Not recap.
2. NAMED IDEAS ONLY — Extract concepts that can be named and remembered.
3. PRACTICAL GROUNDING — Every important idea must have a "this means in practice..." line.
4. HONEST ABOUT QUALITY — Rate honestly. 5 stars = changes how you think. 2 stars = one good idea, padded.
5. CONNECTIONS ARE THE PRODUCT — Always update connections when adding a book.
6. THE LIBRARY GROWS SMARTER — Older entries revisited when new books challenge them.
7. DISAGREE CONSTRUCTIVELY — Name the weakness, cite counter-evidence, suggest stronger version.

CATEGORY TAXONOMY:
- STRATEGY & BUSINESS MODELS
- LEADERSHIP & MANAGEMENT
- PRODUCTIVITY & PERFORMANCE
- PSYCHOLOGY & DECISION-MAKING
- COMMUNICATION & NEGOTIATION
- ENTREPRENEURSHIP & STARTUPS
- INNOVATION & CREATIVITY
- SYSTEMS THINKING & COMPLEXITY
- KNOWLEDGE & LEARNING
- FINANCE & ECONOMICS
- CULTURE & ORGANISATIONS
- BIOGRAPHY & NARRATIVE

You MUST respond with valid JSON matching the schema specified in each request.
Do not include markdown code fences around the JSON. Output raw JSON only."""


BOOK_CARD_PROMPT = """Process this book and produce a full BOOK CARD.

BOOK: {book_title}
DEPTH: {depth}
USER CONTEXT: {user_context}

EXISTING LIBRARY (books already processed):
{existing_library}

Respond with a JSON object matching this exact structure:
{{
  "title": "Full title of the book",
  "author": "Author name(s)",
  "published_year": 2016,
  "reading_time_hours": 5.0,
  "relevance_score": 5,
  "relevance_rationale": "One-line rationale for the score",
  "audience": "Specific audience description",
  "categories": ["Primary Category", "Secondary Category"],
  "core_argument": "2-3 sentences on the central claim",
  "evidence_method": "How the author makes their case and how strong the evidence is",
  "ideas_worth_keeping": [
    {{
      "name": "Memorable label for the idea",
      "explanation": "2-3 sentence explanation",
      "practical": "This means that in practice you should..."
    }}
  ],
  "frameworks_tools": [
    {{
      "name": "Framework name",
      "what_it_does": "Description",
      "when_to_use": "When to apply it",
      "limitation": "One-line limitation"
    }}
  ],
  "what_gets_right": "Where the argument is compelling and evidence strong",
  "what_gets_wrong": "Where argument is weak, overstated, or contradicted",
  "curator_verdict": "One paragraph, first person assessment",
  "connections": {{
    "builds_on": ["Book titles that this book builds on"],
    "precedes": ["Books that introduced these ideas earlier"],
    "challenges": ["Books that argue the opposite"],
    "pairs_well_with": ["Complementary books"],
    "supersedes": ["Books this makes outdated"]
  }},
  "themes": ["Theme names that this book contributes to"],
  "idea_index_entries": [
    {{
      "concept_name": "CONCEPT NAME",
      "definition": "One-sentence definition",
      "related_concepts": ["Other concept names"]
    }}
  ]
}}"""


BATCH_SYNTHESIS_PROMPT = """You have just processed these books:
{book_summaries}

EXISTING LIBRARY:
{existing_library}

Produce a BATCH SYNTHESIS as JSON:
{{
  "connecting_themes": "What themes connect these books?",
  "most_important_ideas": "Most important ideas across multiple books",
  "contradictions": "Any direct contradictions between books in this batch",
  "one_idea_for_tomorrow": "If you could only take one idea into work tomorrow, what would it be?",
  "new_debates": [
    {{
      "question": "The debate question",
      "side_a_position": "Position A",
      "side_a_books": ["Book titles"],
      "side_b_position": "Position B",
      "side_b_books": ["Book titles"],
      "curator_position": "Your assessment",
      "resolution_path": "How to hold both views"
    }}
  ],
  "new_themes": [
    {{
      "name": "Theme name",
      "consensus_view": "What most books agree on",
      "dissenting_view": "What one or more books argue differently",
      "curator_synthesis": "What the evidence suggests",
      "most_useful_book": "Single recommendation"
    }}
  ]
}}"""


MASTER_LOG_PROMPT = """Generate or update the MASTER LOG for the entire library.

ALL BOOKS IN LIBRARY:
{all_books_summary}

ALL CATEGORIES:
{categories_summary}

ALL THEMES:
{themes_summary}

ALL DEBATES:
{debates_summary}

ALL IDEAS IN INDEX:
{ideas_summary}

Produce the complete Master Log as JSON:
{{
  "library_overview": {{
    "total_books": 0,
    "categories_represented": ["list"],
    "date_range": "Earliest to most recent",
    "reading_priority_ranking": [
      {{
        "rank": 1,
        "title": "Book title",
        "rationale": "Why it earns this rank"
      }}
    ]
  }},
  "category_files": [
    {{
      "category_name": "Category",
      "book_count": 0,
      "book_titles": ["titles"],
      "central_debate": "What books collectively argue and where they disagree",
      "best_entry_point": "Which book to read first and why",
      "most_underrated": "Book that deserves more attention",
      "most_overrated": "Book that gets more credit than earned",
      "key_tensions": "2-3 ideas books disagree on",
      "synthesis_insight": "The one thing all best books agree on"
    }}
  ],
  "cross_book_themes": [
    {{
      "theme_name": "Theme",
      "books": ["Book titles"],
      "consensus_view": "What most agree on",
      "dissenting_view": "Different arguments",
      "curator_synthesis": "What evidence suggests",
      "most_useful_book": "Recommendation"
    }}
  ],
  "debates_tensions": [
    {{
      "question": "The debate",
      "side_a": "Position + books",
      "side_b": "Position + books",
      "curator_position": "Your view",
      "resolution_path": "How to hold both"
    }}
  ],
  "curator_picks": {{
    "most_practically_useful": {{"title": "", "reason": ""}},
    "most_intellectually_important": {{"title": "", "reason": ""}},
    "most_underrated": {{"title": "", "reason": ""}},
    "best_for_new_leader": {{"title": "", "reason": ""}},
    "best_for_founder": {{"title": "", "reason": ""}},
    "best_for_clear_thinking": {{"title": "", "reason": ""}},
    "best_for_overwhelmed": {{"title": "", "reason": ""}}
  }},
  "library_gaps": "Topics or perspectives not yet represented and suggested additions"
}}"""


QUERY_PROMPT = """The user is querying their book library.

QUERY: {query}
USER CONTEXT: {user_context}

FULL LIBRARY STATE:
{library_state}

Answer the query by synthesising insights from all relevant books in the library.
Lead with the consensus, then surface debates. Be specific — "read widely" is not an answer.

Respond as JSON:
{{
  "answer": "Full synthesised answer to the query",
  "relevant_books": ["Book titles most relevant to this query"],
  "relevant_concepts": ["Named concepts from the idea index"],
  "recommended_reading_sequence": [
    {{
      "rank": 1,
      "title": "Book title",
      "reason": "Why this book is relevant to the query"
    }}
  ],
  "key_debates": ["Any relevant debates or tensions on this topic"]
}}"""


CATEGORY_UPDATE_PROMPT = """Update the category file for "{category_name}" given these books:

BOOKS IN THIS CATEGORY:
{books_in_category}

Produce an updated category file as JSON:
{{
  "central_debate": "What do books in this category collectively argue? Where are the major disagreements?",
  "best_entry_point": "Which book to read first and why",
  "most_underrated": "The book that deserves more attention",
  "most_overrated": "The book that gets more credit than it earns",
  "key_tensions": "The 2-3 ideas that books in this category disagree on",
  "synthesis_insight": "The one thing all the best books in this category agree on"
}}"""


def format_book_card_markdown(book_data: dict) -> str:
    """Render a book card as beautifully formatted markdown."""
    stars = "⭐" * book_data.get("relevance_score", 3)

    ideas = ""
    for i, idea in enumerate(book_data.get("ideas_worth_keeping", []), 1):
        ideas += f"\n**{i}. {idea['name']}**\n{idea['explanation']}\n*In practice:* {idea['practical']}\n"

    frameworks = ""
    for fw in book_data.get("frameworks_tools", []):
        frameworks += f"\n**{fw['name']}** | {fw['what_it_does']} | Use when: {fw['when_to_use']} | Limitation: {fw['limitation']}"

    connections = book_data.get("connections", {})
    conn_lines = []
    for key, books in connections.items():
        if books:
            label = key.upper().replace("_", " ")
            conn_lines.append(f"**{label}:** {', '.join(books)}")

    categories = " / ".join(book_data.get("categories", []))

    return f"""# BOOK CARD

| Field | Value |
|-------|-------|
| **Title** | {book_data['title']} |
| **Author(s)** | {book_data['author']} |
| **Published** | {book_data.get('published_year', 'Unknown')} |
| **Category** | {categories} |
| **Reading time** | ~{book_data.get('reading_time_hours', '?')} hours |
| **Relevance** | {stars} — {book_data.get('relevance_rationale', '')} |
| **Who it's for** | {book_data.get('audience', '')} |

---

## THE CORE ARGUMENT

{book_data.get('core_argument', '')}

## THE EVIDENCE & METHOD

{book_data.get('evidence_method', '')}

## THE IDEAS WORTH KEEPING
{ideas}

## THE FRAMEWORKS & TOOLS
{frameworks}

## WHAT THE BOOK GETS RIGHT

{book_data.get('what_gets_right', '')}

## WHAT THE BOOK GETS WRONG (OR INCOMPLETE)

{book_data.get('what_gets_wrong', '')}

## CURATOR'S VERDICT

{book_data.get('curator_verdict', '')}

## CONNECTIONS TO OTHER BOOKS

{chr(10).join(conn_lines)}
"""
