"""Exception type for the city-scoped routes. Routers/services
raise `DomainError(code, message, status_code)`, one FastAPI exception
handler (`backend/main.py`) turns it into an `ErrorResponse` body -- no
route hand-rolls its own error JSON shape.
"""
from __future__ import annotations

from backend.schemas import ErrorCode


class DomainError(Exception):
    def __init__(self, code: ErrorCode, message: str, status_code: int = 404):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)
