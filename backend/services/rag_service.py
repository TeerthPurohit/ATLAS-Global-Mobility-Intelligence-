"""Service layer wrapping RAG pipeline and conversation session history (FR-6, FR-8).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Generator

RAG_DIR = Path(__file__).resolve().parents[2] / "rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

import rag_pipeline  # noqa: E402
import session_store  # noqa: E402


def answer_question(question: str, session_id: str | None = None) -> dict[str, Any]:
    return rag_pipeline.answer(question=question, session_id=session_id)


def stream_answer(question: str, session_id: str | None = None) -> Generator[dict[str, Any], None, None]:
    yield from rag_pipeline.answer_stream(question=question, session_id=session_id)


def get_history(session_id: str) -> list[dict[str, Any]] | None:
    if not session_store.session_exists(session_id):
        return None
    return session_store.get_session_history(session_id)
