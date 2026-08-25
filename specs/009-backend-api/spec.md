# SPEC-009: Backend API

Owner: solo builder · Status: done · Layer: 5 · Depends on: SPEC-006, SPEC-007, SPEC-008

## Business Goal

Serve predictions and chat over REST so the frontend (and any external
caller) can reach the platform's outputs. Thin layer — no business logic
that belongs in dbt/algorithms/models.

## Functional Requirements

- FR-1: `main.py` — FastAPI app, mounts routers.
- FR-2: `routers/predictions.py` — `GET /predict/demand`, `GET /predict/fare`.
- FR-3: `routers/zones.py` — `GET /zones` (list/detail for map rendering).
- FR-4: `routers/chat.py` — `POST /chat`, wraps `rag_pipeline.py`.
- FR-5: `services/model_service.py` — loads precomputed artifacts once at
  startup (rule 8 — no training or raw-table scans on a request path).
- FR-6: `services/rag_service.py` — wraps `rag/rag_pipeline.py`.
- FR-7: `schemas.py` — Pydantic request/response models for every route.
- FR-8 (added 2026-08-06): `GET /chat/history/{session_id}` — returns the
  stored turn history for a session via `rag/session_store.py`. 404 if the
  session_id doesn't exist (don't silently return an empty list — that
  hides a client bug where it's using the wrong id).
- FR-9 (added 2026-08-06): `WS /chat/stream` — WebSocket endpoint. Client
  sends `{session_id?: str, question: str}`; server creates a session_id
  if absent (send it back as the first frame so the client can persist
  it), then streams `rag_pipeline.py`'s streaming generator chunk-by-chunk
  as the LLM produces them, ending with a final frame containing the
  complete answer + route + sql (if any) + session_id, mirroring the
  shape of the plain `/chat` response so both paths are usable by the same
  frontend chat component.

## API Design

| Route | Method | Request | Response |
|---|---|---|---|
| `/predict/demand` | GET | `zone_id`, `hour`, `day_of_week` | predicted count, model name used |
| `/predict/fare` | GET | `pickup_zone`, `dropoff_zone`, `hour` | predicted fare |
| `/zones` | GET | none / `zone_id` | zone metadata + centroid |
| `/chat` | POST | `question: str`, `session_id?: str` | `answer`, `route: "sql"\|"retrieval"`, `sql?: str`, `session_id` |
| `/chat/history/{session_id}` | GET | none | list of `{role, content, route, sql, timestamp}` |
| `/chat/stream` | WS | `{session_id?, question}` frames in | streamed answer chunks, final frame with full answer/route/sql/session_id |

Standard REST status codes (200, 400 for bad zone IDs, 500 only for genuine
server errors — no swallowing errors into 200 with an error field).

## Non-Functional Requirements

Startup load of artifacts must complete before the app accepts traffic — no
lazy-load-on-first-request race that serves a 500 or a cold-model response.

## Testing

One happy-path test per route (standards.md testing bar — no exhaustive
edge-case matrix without a demonstrated need).

## Acceptance Criteria

- [ ] All 6 routes implemented and documented in the response table above.
- [ ] Model/RAG artifacts loaded once at startup, verified by inspection of
      `model_service.py` (no per-request reload).
- [ ] Session history persists across separate `/chat` or `/chat/stream`
      calls sharing the same `session_id`, verified by a real round-trip
      test (send two turns, confirm the second sees the first via
      `/chat/history/{session_id}`).
- [ ] `/chat/stream` delivers multiple incremental chunks before its final
      frame (not the whole answer in one frame pretending to be a stream).
- [ ] One passing test per route.
