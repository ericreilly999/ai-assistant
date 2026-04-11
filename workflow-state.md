# Workflow State

> Last updated: 2026-04-11 by Project Manager

## Project
**Name**: AI Assistant MVP  
**Route-to-live**: Standard (dev → staging → prod)  
**Started**: 2026-03-16

---

## Current Stage

**Stage**: 4 — QA Validation (Dev Environment)  
**Status**: In Progress — one infrastructure fix in flight, then manual testing by Eric  
**Active agent**: DevOps Engineer (T-12 unblock — committing callback_urls fix)  
**Started**: 2026-04-08

---

## Gate Status

| Gate | Required | Status |
|------|----------|--------|
| Spec complete + TODO.md written | Stage 0 → 1 | ✅ |
| All QA test-writing tasks complete | Stage 1 → 2 | ✅ |
| All DEV tasks complete, code on main | Stage 2 → 3 | ✅ |
| Dev environment live + smoke tests pass | Stage 3 → 4 | ✅ |
| QA sign-off on dev (test-signoff.md) | Stage 4 → 5 | ⏳ |
| Staging live + smoke tests pass | Stage 5 → 6 | ❌ |
| QA sign-off on staging (test-signoff.md) | Stage 6 → 7 | ❌ |
| **Human approval for production** | Stage 7 | ❌ |

---

## Next Action

**DevOps Engineer** — commit `terraform/environments/dev/terraform.tfvars` (callback_urls fix), `.gitignore`, and `project-status.md` then push to `main`. CI/CD will apply Terraform and register the Expo redirect URIs with the Cognito app client.

Once CI/CD confirms success: **Eric** runs the T-12 manual smoke test (sign-in via Cognito hosted UI, chat round-trip, proposal approve/reject). Steps are documented in `test-signoff.md` — Phase 4 section.

After T-12 passes: **QA Engineer** runs T-16 (provider OAuth flows) and T-17 (full live end-to-end test + Stage 4 sign-off).

---

## Active Blockers

| Blocker | Owner | Resolution |
|---------|-------|------------|
| Cognito callback_urls empty — Expo redirect URIs not registered | DevOps Engineer | Commit + push terraform.tfvars (fix already written locally) |
