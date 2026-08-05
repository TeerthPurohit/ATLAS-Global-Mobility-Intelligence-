# SPEC-011: Deployment & DevOps

Owner: solo builder · Status: not started · Layer: 5 · Depends on: SPEC-009, SPEC-010

## Business Goal

A live, reachable demo plus a portfolio-grade repo — both matter equally
(see `project_plan.md` closing notes).

## Functional Requirements

- FR-1: Precompute deployment artifacts (marts + model outputs + RAG
  index) into a slimmed DuckDB file — see ADR-005.
- FR-2: Deploy `backend/` to a free-tier host (Render/Railway).
- FR-3: Deploy `frontend/` to Vercel/Netlify, pointed at the deployed
  backend.
- FR-4: Root `README.md`: project summary, architecture diagram, model
  comparison table, "why these technical choices" section (linking the
  ADRs), live demo link.
- FR-5: Record a short demo video/GIF as a backup for when the live deploy
  is down (free-tier hosts can go cold).
- FR-6: CI: lint + test on push (see `.github/workflows/ci.yml`) — kept
  intentionally small, see `docs/architecture/Infrastructure.md` on what's
  out of scope.

## Non-Functional Requirements

Deployed DuckDB file ships marts/predictions only, never the raw 8-10M row
trips table (rule 8, ADR-005).

## Testing

Post-deploy smoke test: both UC-3 (numeric chat) and UC-4 (explanatory
chat) verified against the live URL, not just local dev.

## Acceptance Criteria

- [ ] Backend and frontend both deployed and reachable.
- [ ] README complete with architecture diagram + model comparison + ADR
      links.
- [ ] Demo GIF/video recorded.
- [ ] CI runs lint + test on push.
