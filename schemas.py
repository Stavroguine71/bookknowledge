"""
Pydantic request/response schemas for the API.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── Requests ────────────────────────────────────────────────────────

class ProcessBookRequest(BaseModel):
    book_title: str = Field(..., description="Title of the book to process", min_length=1)
    depth: str = Field(
        default="FULL",
        description="Processing depth: FULL, CORE, or QUICK",
        pattern="^(FULL|CORE|QUICK)$",
    )
    user_context: str = Field(
        default="Knowledge worker building a personal library",
        description="Who you are and what you're trying to do",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "book_title": "Deep Work by Cal Newport",
                    "depth": "FULL",
                    "user_context": "Engineering manager trying to protect team focus time",
                }
            ]
        }
    }


class BatchProcessRequest(BaseModel):
    book_titles: list[str] = Field(
        ...,
        description="List of book titles to process",
        min_length=1,
        max_length=20,
    )
    depth: str = Field(default="FULL", pattern="^(FULL|CORE|QUICK)$")
    user_context: str = Field(
        default="Knowledge worker building a personal library",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "book_titles": [
                        "Deep Work by Cal Newport",
                        "Atomic Habits by James Clear",
                        "The One Thing by Gary Keller",
                    ],
                    "depth": "FULL",
                    "user_context": "Productivity-focused knowledge worker",
                }
            ]
        }
    }


class QueryRequest(BaseModel):
    query: str = Field(..., description="Your question for the library", min_length=1)
    user_context: str = Field(
        default="Knowledge worker",
        description="Your role/situation for personalised answers",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What does the library say about building habits?",
                    "user_context": "New manager, 3 months in, building team routines",
                }
            ]
        }
    }


class QuickAddRequest(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    category: str
    core_idea: str
    best_idea: str
    worth_reading: str = Field(
        ...,
        description="YES / ONLY IF SPECIFIC INTEREST / NO — read X instead",
    )
    connects_to: list[str] = Field(default_factory=list)
