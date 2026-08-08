"""Chat router endpoints: POST /chat, GET /chat/history/{session_id}, and WS /chat/stream (FR-4, FR-8, FR-9).
"""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.schemas import ChatMessage, ChatRequest, ChatResponse
from backend.services import rag_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask the hybrid RAG chat",
    description="Numeric questions compile to real SQL via a QueryPlan (no LLM-authored SQL "
    "text, SPEC-013 FR-10); explanatory questions retrieve grounded insight docs.",
)
def post_chat(req: ChatRequest) -> ChatResponse:
    # city_id now actually routes (SPEC-013 FR-11) -- old clients that never
    # send it default to "nyc"/full_rag, identical behavior to before.
    res = rag_service.answer_question(question=req.question, session_id=req.session_id, city_id=req.city_id or "nyc")
    return ChatResponse(
        answer=res["answer"],
        route=res["route"],
        sql=res.get("sql"),
        session_id=res["session_id"],
        city_id=req.city_id,
        area_id=req.area_id,
    )


@router.get("/history/{session_id}", response_model=list[ChatMessage])
def get_chat_history(session_id: str) -> list[ChatMessage]:
    history = rag_service.get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail=f"Session history for id '{session_id}' not found")
    return [
        ChatMessage(
            role=msg["role"],
            content=msg["content"],
            route=msg.get("route"),
            sql=msg.get("sql"),
            timestamp=str(msg["timestamp"]),
        )
        for msg in history
    ]


@router.websocket("/stream")
async def websocket_chat_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        data_str = await websocket.receive_text()
        data = json.loads(data_str)
        question = data.get("question")
        if not question:
            await websocket.send_json({"error": "question is required"})
            await websocket.close(code=1008)
            return

        session_id = data.get("session_id")
        for chunk_item in rag_service.stream_answer(question=question, session_id=session_id):
            await websocket.send_json(chunk_item)

        await websocket.close()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"error": str(exc)})
            await websocket.close(code=1011)
        except Exception:
            pass
