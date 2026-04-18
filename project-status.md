# Project Status — integreat

> Last updated: 2026-04-18

## Summary

Stage 4 (QA Validation on Dev) is in progress. Phase 13 (LLM Tool Use Orchestrator) is complete and deployed — the keyword-based intent classifier has been replaced by a Bedrock Converse agent loop with 9 tool definitions, read-before-write ID validation, and 257 tests passing. CI/CD hardening (Checkov enforcement, auto-fmt PR flow, coverage gate) is also merged. T-12 manual smoke test is ready for Eric to execute.

## What We Just Completed

- 2026-04-18 — Phase 13 security fix: `list_id` validation against prior `get_task_lists` results; `_extract_prior_task_ids` now scoped to `get_tasks` only; dead `classify()` removed — 257 tests green (pushed to main)
- 2026-04-18 — Phase 13 (LLM Tool Use Orchestrator) merged: PR #12 — `tool_definitions.py`, `tool_handlers.py`, agent loop in `orchestrator.py`, `intent.py` deleted, 254 tests
- 2026-04-18 — CI/CD hardening merged: PR #11 — Checkov enforcement, auto-fmt PR flow, 80% coverage gate
- 2026-04-18 — Deploy #7: `exp://192.168.6.249:8081` registered in Cognito callback URLs
- 2026-04-18 — Deploy #6: `ai-assistant://` native scheme registered in Cognito
- 2026-04-18 — PR #10 merged: intent classification fix (META_HINTS)

## What's In Progress

- Dev deploy triggered by Phase 13 security fix push to main (Deploy #8 in flight)
- Awaiting Eric approval to invoke DevOps for zombie infra teardown (~$95–128/month savings)

## What's Coming Next

1. **Eric (human action)** — Approve or defer zombie infra teardown (RDS, ECR, ALB, NAT Gateway — $40.47/month waste)
2. **Eric (human action)** — T-12: Manual smoke test (sign-in → chat → proposal → approve/reject → sign-out)
3. **DevOps Engineer** — Align `deploy-dev.yml` gate with `pytest --cov-fail-under=80` (currently uses `unittest discover`)
4. **QA Engineer** — T-16: Provider OAuth flows (Google + Microsoft)
5. **QA Engineer** — T-17: Full live end-to-end test + Stage 4 sign-off
6. **DevOps Engineer** — T-18: Staging CI/CD pipeline (after Stage 4 sign-off)

## Blockers

None.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Zombie infra ($40.47/mo) — RDS, ECR, ALB, NAT Gateway not torn down | H | H | DevOps teardown — awaiting Eric approval |
| Google/Microsoft OAuth app not registered for dev redirect URIs | M | H | Eric to verify redirect URI registration during T-16 |
| deploy-dev.yml uses unittest not pytest — coverage gate not enforced on deploy path | M | M | DevOps follow-up task to align with ci.yml |
| Staging AWS infrastructure does not yet exist (IAM role, S3 bucket) | L | M | T-18 covers this; not needed until Stage 4 QA sign-off is complete |
