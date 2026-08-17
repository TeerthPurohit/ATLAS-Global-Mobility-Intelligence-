"""Chat router endpoints: POST /chat, GET /chat/history/{session_id}, and WS /chat/stream (FR-4, FR-8, FR-9).
"""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger

from backend.schemas import ChatMessage, ChatRequest, ChatResponse
from backend.services import rag_service

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
    summary="Ask the hybrid RAG chat (canonical, city_id optional in body)",
    description="Numeric questions compile to real SQL via a QueryPlan (no LLM-authored SQL "
    "text, SPEC-013 FR-10); explanatory questions retrieve grounded insight docs. "
    "`city_id` defaults to nyc if omitted. `/api/cities/{city_id}/chat` calls this identical "
    "rag_service path with city_id required in the URL and a 404 if that city doesn't "
    "resolve -- not a separate implementation.",
)
def post_chat(req: ChatRequest) -> ChatResponse:
    # city_id now actually routes (SPEC-013 FR-11) -- old clients that never
    # send it default to "nyc"/full_rag, identical behavior to before.
    routed_city_id = req.city_id or "nyc"
    logger.info("POST /chat step=start city_id={} session_id={} question={!r}", routed_city_id, req.session_id, req.question)
    try:
        res = rag_service.answer_question(question=req.question, session_id=req.session_id, city_id=routed_city_id)
    except Exception:
        logger.exception("POST /chat step=rag_service.answer_question failed city_id={}", routed_city_id)
        raise
    logger.info("POST /chat step=done route={} session_id={}", res.get("route"), res.get("session_id"))
    return ChatResponse(
        answer=res["answer"],
        route=_normalize_route(res["route"]),
        sql=res.get("sql"),
        session_id=res["session_id"],
        city_id=routed_city_id,
        area_id=req.area_id,
    )


@router.get("/history/{session_id}", response_model=list[ChatMessage])
def get_chat_history(session_id: str) -> list[ChatMessage]:
    logger.info("GET /chat/history step=start session_id={}", session_id)
    history = rag_service.get_history(session_id)
    if history is None:
        logger.warning("GET /chat/history step=not_found session_id={}", session_id)
        raise HTTPException(status_code=404, detail=f"Session history for id '{session_id}' not found")
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


@router.websocket("/stream")
async def websocket_chat_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("WS /chat/stream step=accepted")
    try:
        data_str = await websocket.receive_text()
        data = json.loads(data_str)
        question = data.get("question")
        if not question:
            logger.warning("WS /chat/stream step=validation_failed reason=missing_question")
            await websocket.send_json({"error": "question is required"})
            await websocket.close(code=1008)
            return

        session_id = data.get("session_id")
        # city_id/area_id route the stream exactly like POST /chat (FR-11);
        # city_id defaults to "nyc" for callers that predate it.
        city_id = data.get("city_id") or "nyc"
        area_id = data.get("area_id")
        logger.info("WS /chat/stream step=streaming city_id={} session_id={}", city_id, session_id)
        for chunk_item in rag_service.stream_answer(question=question, session_id=session_id, city_id=city_id):
            if chunk_item.get("type") == "done":
                payload = dict(chunk_item.get("payload") or {})
                payload["city_id"] = city_id
                payload["area_id"] = area_id
                payload["route"] = _normalize_route(payload.get("route"))
                chunk_item = {**chunk_item, "payload": payload}
            await websocket.send_json(chunk_item)

        await websocket.close()
        logger.info("WS /chat/stream step=done")
    except WebSocketDisconnect:
        logger.info("WS /chat/stream step=client_disconnected")
    except Exception as exc:
        # Log the real exception server-side for investigation; never forward
        # str(exc) to the client -- it can contain internal details (DB
        # hostnames/ports, driver error text) that are none of the caller's
        # business. Found via /debug 2026-08-13: an unreachable RDS Postgres
        # connection string reached the frontend verbatim through this path
        # before session_store.py/prediction_log.py were made to degrade
        # gracefully (the actual root-cause fix); this is the defense-in-depth
        # backstop for whatever the next unexpected failure turns out to be.
        logger.exception("chat stream failed")
        try:
            await websocket.send_json({"error": "Something went wrong answering this question. Please try again."})
            await websocket.close(code=1011)
        except Exception:
            pass
