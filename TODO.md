# AI Assistant — Master Todo List

Last updated: 2026-04-06

## Phase 1 — Housekeeping / Quickfixes ✅
- [x] Fix .gitignore: `dist/`, `backend/.local/`, `terraform/.terraform/` (already correct)
- [x] Fix mobile `api.ts` default port 3000 → 8787
- [x] Wire `CORS_ALLOWED_ORIGINS` env var in `response.py` instead of hardcoding `"*"`
- [x] Fix `prod` `tfvars.example`: `mock_provider_mode=false`, real prod CORS origin placeholder
- [x] Fix `start-provider-auth.ps1` to read `LOCAL_SERVER_PORT` instead of hardcoding 8787
- [x] Add graceful HTML error page to OAuth start routes when credentials are not configured

## Phase 2 — Local Provider Integrations ✅
- [ ] Verify Google OAuth flow end-to-end locally (start → redirect → token exchange → dev_store)
- [ ] Verify Microsoft OAuth flow end-to-end locally
- [ ] Verify Plaid sandbox bootstrap and account/transaction reads
- [ ] Verify Google Calendar live reads and create_event write
- [ ] Verify Google Tasks live reads and create_task write
- [ ] Verify Google Drive live document list and export
- [ ] Verify Microsoft Calendar live reads and create_event write
- [ ] Verify Microsoft Todo live reads and create_task write
- [x] Add `update_task()` and `complete_task()` to `google_tasks.py` + wire into `_execute_live()`
- [x] Add `update_task()` and `complete_task()` to `microsoft_todo.py` + wire into `_execute_live()`

## Phase 3 — Orchestrator Completeness ✅
- [x] Add `tasks` intent branch to `intent.py` `classify_message()`
- [x] Replace hardcoded general intent fallback with meaningful response
- [x] Replace hardcoded meeting prep agenda in `_live_meeting_prep_plan()` with real Drive content
- [x] Add structured request logging: `request_id`, `route`, `provider`, `action_type`, `latency`
- [x] Implement dynamic `risk_level` classification in `consent.py`
- [x] Expand `_execute_live()` to cover `microsoft_calendar` and remaining action types

## Phase 4 — Test Coverage ✅
- [x] Expand `test_handler.py`: Microsoft OAuth, dev routes, 404, OPTIONS, execute happy path, 502, all intent plan routes
- [x] Expand `test_orchestrator.py`: meeting_prep live, execute edge cases, window-finding, provider ValueError paths
- [x] Expand `test_oauth.py`: code exchange, token refresh, state mismatch, `_required()` missing var
- [x] Expand `test_consent.py`: `approved=False` rejection, missing `expires_at`
- [x] Expand `test_providers.py`: HTTP-mocked live adapter methods and edge cases
- [x] Expand `test_dev_store.py`: `clear_tokens`, Plaid status, `expires_at`, malformed file, merge behavior
- [x] Configure `pyproject.toml` with pytest, mypy, ruff
- [x] Add backend lint (ruff) and type check (mypy) to CI
- [x] Add tflint and tfsec/checkov to CI terraform-validate job
- [x] Add Lambda package build + artifact validation to CI

## Phase 5 — Bedrock Integration ✅
- [x] Implement Bedrock Converse integration: replace keyword classifier with model router/planner
- [x] Implement Bedrock guardrail invocation on user input and model output
- [x] Add `bedrock_guardrail` and `bedrock_prompt` Terraform resources

## Phase 6 — AWS Deployment (requires credentials + infra) ✅
- [x] Implement Secrets Manager runtime loading at Lambda cold start
- [x] Fix Plaid credentials to load via Secrets Manager in Lambda
- [x] Add `kms_key` Terraform module for CMK encryption of Secrets Manager
- [x] Add Lambda alias resource to `lambda_service` Terraform module
- [x] Add `acm_certificate` and `route53_records` Terraform modules
- [x] Add Cognito hosted UI domain resource to Terraform
- [x] Expand `service_observability`: p50/p95/p99 alarms, Bedrock failure, provider errors, throttle

## Phase 7 — Mobile
- [ ] Implement Cognito auth flow: sign-in screen, token storage, JWT headers on API calls
- [ ] Add proposal reject button + rejection path in `App.tsx`
- [ ] Add mobile error handling: surface API errors to user
- [ ] Add scroll-to-bottom and multi-turn conversation history
- [ ] Add `resource_type`, `risk_level`, payload details to `ActionProposalCard`
- [ ] Add mobile unit tests: chat screen, approval modal, token handling, provider connection state

## Phase 8 — Prompt Regression Tests
- [ ] Build prompt regression test suite: golden cases for all intents + security cases (injection, write-without-consent)
