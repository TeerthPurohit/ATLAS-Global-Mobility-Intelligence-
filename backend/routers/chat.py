"""Chat router endpoints: POST /chat, GET /chat/history/{session_id}, and WS /chat/stream (FR-4, FR-8, FR-9).
"""
from __future__ import annotations  # noqa: I001

import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from loguru import logger

from backend.errors import DomainError
from backend.registry import CITY_ID
from backend.schemas import ChatMessage, ChatRequest, ChatResponse, ChatSessionSummary, ErrorCode, NewSessionResponse
from backend.services import auth_service, chat_session_service, rag_service

router = APIRouter(prefix="/chat", tags=["chat"])

_CHAT_ROUTE_VALUES = frozenset({"numeric", "explanatory"})


def _normalize_route(route: str | None) -> str:
    """Frontend ChatRoute contract is numeric | explanatory. The
    context-only tier's internal "context_grounded" label (and any legacy
    row) is the explanatory family -- normalized here at the API boundary."""
    return route if route in _CHAT_ROUTE_VALUES else "explanatory"


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask the hybrid RAG chat",
    description="Numeric questions compile to real SQL via a QueryPlan (no LLM-authored SQL "
    "text, SPEC-013 FR-10); explanatory questions retrieve grounded insight docs.",
)
def post_chat(req: ChatRequest, current_user: dict = Depends(auth_service.get_current_user)) -> ChatResponse:  # noqa: B008 -- FastAPI's Depends() idiom
    logger.info("POST /chat step=start session_id={} question={!r}", req.session_id, req.question)
    try:
        res = rag_service.answer_question(question=req.question, session_id=req.session_id, user_id=current_user["id"])
    except Exception:
        logger.exception("POST /chat step=rag_service.answer_question failed")
        raise
    logger.info("POST /chat step=done route={} session_id={}", res.get("route"), res.get("session_id"))
    return ChatResponse(
        answer=res["answer"],
        route=_normalize_route(res["route"]),
        sql=res.get("sql"),
        session_id=res["session_id"],
        city_id=CITY_ID,
        area_id=req.area_id,
    )


@router.get("/history/{session_id}", response_model=list[ChatMessage])
def get_chat_history(session_id: str, current_user: dict = Depends(auth_service.get_current_user)) -> list[ChatMessage]:  # noqa: B008 -- FastAPI's Depends() idiom
    logger.info("GET /chat/history step=start session_id={}", session_id)
    history = rag_service.get_history(session_id, user_id=current_user["id"])
    if history is None:
        logger.warning("GET /chat/history step=not_found session_id={}", session_id)
        raise DomainError(ErrorCode.SESSION_NOT_FOUND, f"Session history for id '{session_id}' not found", 404)
    logger.info("GET /chat/history step=done session_id={} messages={}", session_id, len(history))
    return [
        ChatMessage(
            role=msg["role"],
            content=msg["content"],
            route=_normalize_route(msg.get("route")),
            sql=msg.get("sql"),
            timestamp=str(msg["timestamp"]),
        )
        for msg in history
    ]


@router.post("/sessions", response_model=NewSessionResponse)
def create_session(current_user: dict = Depends(auth_service.get_current_user)) -> NewSessionResponse:  # noqa: B008 -- FastAPI's Depends() idiom
    logger.info("POST /chat/sessions step=start user_id={}", current_user["id"])
    session_id = chat_session_service.create_or_reuse_session(current_user["id"])
    logger.info("POST /chat/sessions step=done session_id={}", session_id)
    return NewSessionResponse(session_id=session_id)


@router.get("/sessions", response_model=list[ChatSessionSummary])
def list_sessions(current_user: dict = Depends(auth_service.get_current_user)) -> list[ChatSessionSummary]:  # noqa: B008 -- FastAPI's Depends() idiom
    logger.info("GET /chat/sessions step=start user_id={}", current_user["id"])
    sessions = rag_service.list_sessions(user_id=current_user["id"])
    logger.info("GET /chat/sessions step=done count={}", len(sessions))
    return [ChatSessionSummary(**s) for s in sessions]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, current_user: dict = Depends(auth_service.get_current_user)) -> dict:  # noqa: B008 -- FastAPI's Depends() idiom
    logger.info("DELETE /chat/sessions step=start session_id={}", session_id)
    had_messages = rag_service.delete_history(session_id, user_id=current_user["id"])
    had_bookkeeping_row = chat_session_service.delete_session_row(session_id, user_id=current_user["id"])
    if not had_messages and not had_bookkeeping_row:
        logger.warning("DELETE /chat/sessions step=not_found session_id={}", session_id)
        raise DomainError(ErrorCode.SESSION_NOT_FOUND, f"Session '{session_id}' not found", 404)
    logger.info("DELETE /chat/sessions step=done session_id={}", session_id)
    return {"ok": True}


@router.post("/stream")
def stream_chat(
    req: ChatRequest, current_user: dict = Depends(auth_service.get_current_user)  # noqa: B008 -- FastAPI's Depends() idiom
) -> StreamingResponse:
    """Server-Sent Events chat stream (ADR-014 follow-up: replaces the prior
    WebSocket route). Vercel's rewrites() proxy only forwards plain HTTP
    request/response cycles to an external destination -- there is no
    documented support for proxying a WS upgrade through to a backend that
    isn't itself a Vercel Function, so a WS client connecting through the
    deployed frontend's /api/* proxy never actually upgraded; the request
    arrived at the backend as a plain GET and 404'd. SSE is plain HTTP
    streaming, which the same rewrite already proxies correctly (proven by
    every other route)."""
    logger.info("POST /chat/stream step=start session_id={}", req.session_id)

    def event_stream():
        try:
            for chunk_item in rag_service.stream_answer(
                question=req.question, session_id=req.session_id, user_id=current_user["id"]
            ):
                if chunk_item.get("type") == "done":
                    payload = dict(chunk_item.get("payload") or {})
                    payload["city_id"] = CITY_ID
                    payload["area_id"] = req.area_id
                    payload["route"] = _normalize_route(payload.get("route"))
                    chunk_item = {**chunk_item, "payload": payload}
                yield f"data: {json.dumps(chunk_item)}\n\n"
            logger.info("POST /chat/stream step=done")
        except Exception as exc:  # noqa: BLE001, F841
            # Log the real exception server-side for investigation; never forward
            # str(exc) to the client -- it can contain internal details (DB
            # hostnames/ports, driver error text) that are none of the caller's
            # business. Found via /debug 2026-08-13: an unreachable RDS Postgres
            # connection string reached the frontend verbatim through this path
            # before session_store.py/prediction_log.py were made to degrade
            # gracefully (the actual root-cause fix); this is the defense-in-depth
            # backstop for whatever the next unexpected failure turns out to be.
            logger.exception("chat stream failed")
            yield f"data: {json.dumps({'error': 'Something went wrong answering this question. Please try again.'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
