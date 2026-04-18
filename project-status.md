# Project Status — AI Assistant MVP

> Last updated: 2026-04-18

## Summary

Stage 4 (QA Validation on Dev) is in progress. A P2 intent classification bug was found during T-12 smoke testing: conversational follow-up questions (e.g., "Which calendars are u checking?", "which task lists can you use?") were being misrouted to data-fetch and write-proposal handlers instead of returning conversational responses. The fix has been implemented and all 132 tests pass. A PR is ready for code review before merge and redeploy. T-12 can resume after the fix lands.

## What We Just Completed

- 2026-04-18 — Intent classification fix: META_HINTS pre-check in `intent.py` + `_tasks_read_plan` in `orchestrator.py` — all 132 tests green (PR pending review)
- 2026-04-18 — 5 new regression tests added to `test_prompt_regression.py` covering conversational meta-questions and tasks read/write split
- 2026-04-18 — Deploy #6: `ai-assistant://` registered in Cognito callback/logout URLs (PR #8 merged)
- 2026-04-18 — PR #7 merged: `makeRedirectUri()` now explicit with `{ native: 'ai-assistant://' }` + 8 new contract tests + postmortem
- 2026-04-18 — PR #6 merged: README fully rewritten with current architecture, CI/CD, branching, and config

## What's In Progress

Code review of intent classification fix PR — App Engineer changes + QA regression tests.

## What's Coming Next

1. **Code Reviewer** — Review and merge intent classification PR
2. **DevOps Engineer** — Redeploy Lambda with fix (push to main triggers CI/CD)
3. **Eric (human action)** — T-12: Re-run manual smoke test after redeployment (sign-in → chat → proposal → approve/reject → sign-out)
4. **QA Engineer** — T-16: Provider OAuth flows (Google + Microsoft)
5. **QA Engineer** — T-17: Full live end-to-end test + Stage 4 sign-off
6. **DevOps Engineer** — T-18: Staging CI/CD pipeline (after Stage 4 sign-off)

## Blockers

None.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Google/Microsoft OAuth app not registered for dev redirect URIs | M | H | Eric to verify redirect URI registration in Google/Microsoft developer consoles during T-16 |
| Staging AWS infrastructure does not yet exist (IAM role, S3 bucket) | L | M | T-18 covers this; not needed until Stage 4 QA sign-off is complete |
| Production go-live blocked if staging reveals systemic issues | L | H | Full live provider test suite in Stage 4 reduces staging risk |
