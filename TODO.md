# AI Assistant — Master Todo List

Last updated: 2026-04-19

> **Owner key**: `[DEV]` Application Engineer · `[QA]` QA Engineer · `[DEVOPS]` DevOps Engineer · `[REQ]` Requirement Analyst · `[HUMAN]` Eric (manual action required)

---

## Phase 1 — Housekeeping / Quickfixes ✅ `[DEV]`
- [x] Fix .gitignore: `dist/`, `backend/.local/`, `terraform/.terraform/` (already correct)
- [x] Fix mobile `api.ts` default port 3000 → 8787
- [x] Wire `CORS_ALLOWED_ORIGINS` env var in `response.py` instead of hardcoding `"*"`
- [x] Fix `prod` `tfvars.example`: `mock_provider_mode=false`, real prod CORS origin placeholder
- [x] Fix `start-provider-auth.ps1` to read `LOCAL_SERVER_PORT` instead of hardcoding 8787
- [x] Add graceful HTML error page to OAuth start routes when credentials are not configured

## Phase 2 — Local Provider Integrations ✅ `[DEV]`
- [x] Verify Google OAuth flow end-to-end locally (start → redirect → token exchange → dev_store)
- [x] Verify Microsoft OAuth flow end-to-end locally
- [x] Verify Plaid sandbox bootstrap and account/transaction reads
- [x] Verify Google Calendar live reads and create_event write
- [x] Verify Google Tasks live reads and create_task write
- [x] Verify Google Drive live document list and export
- [x] Verify Microsoft Calendar live reads and create_event write
- [x] Verify Microsoft Todo live reads and create_task write
- [x] Add `update_task()` and `complete_task()` to `google_tasks.py` + wire into `_execute_live()`
- [x] Add `update_task()` and `complete_task()` to `microsoft_todo.py` + wire into `_execute_live()`

## Phase 3 — Orchestrator Completeness ✅ `[DEV]`
- [x] Add `tasks` intent branch to `intent.py` `classify_message()`
- [x] Replace hardcoded general intent fallback with meaningful response
- [x] Replace hardcoded meeting prep agenda in `_live_meeting_prep_plan()` with real Drive content
- [x] Add structured request logging: `request_id`, `route`, `provider`, `action_type`, `latency`
- [x] Implement dynamic `risk_level` classification in `consent.py`
- [x] Expand `_execute_live()` to cover `microsoft_calendar` and remaining action types

## Phase 4 — Test Coverage ✅ `[QA]` `[DEV]`
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

## Phase 5 — Bedrock Integration ✅ `[DEV]`
- [x] Implement Bedrock Converse integration: replace keyword classifier with model router/planner
- [x] Implement Bedrock guardrail invocation on user input and model output
- [x] Add `bedrock_guardrail` and `bedrock_prompt` Terraform resources

## Phase 6 — AWS Deployment ✅ `[DEVOPS]` `[DEV]`
- [x] Implement Secrets Manager runtime loading at Lambda cold start
- [x] Fix Plaid credentials to load via Secrets Manager in Lambda
- [x] Add `kms_key` Terraform module for CMK encryption of Secrets Manager
- [x] Add Lambda alias resource to `lambda_service` Terraform module
- [x] Add `acm_certificate` and `route53_records` Terraform modules
- [x] Add Cognito hosted UI domain resource to Terraform
- [x] Expand `service_observability`: p50/p95/p99 alarms, Bedrock failure, provider errors, throttle

## Phase 7 — Mobile ✅ `[DEV]`
- [x] Implement Cognito auth flow: sign-in screen, token storage, JWT headers on API calls
- [x] Add proposal reject button + rejection path in `App.tsx`
- [x] Add mobile error handling: surface API errors to user
- [x] Add scroll-to-bottom and multi-turn conversation history
- [x] Add `resource_type`, `risk_level`, payload details to `ActionProposalCard`
- [x] Add mobile unit tests: chat screen, approval modal, token handling, provider connection state

## Phase 8 — Prompt Regression Tests ✅ `[QA]`
- [x] Build prompt regression test suite: golden cases for all intents + security cases (injection, write-without-consent)

---

## Phase 9 — Dev Environment Validation `[DEVOPS]` `[QA]`
> **Stage 4: QA Validation (Dev)**. Gate to Stage 5: QA sign-off in test-signoff.md

### T-10 — Configure Cognito Hosted UI Domain `[DEVOPS]`
**Status**: [x] Done — 2026-04-10  
**Depends On**: —  
- [x] Provision Cognito hosted UI custom domain in Terraform (`cognito_user_pool` module)
- [x] Apply to dev environment — `terraform apply`
- [x] Confirm hosted UI URL is reachable
- [x] Update `deployment-log.md` with the domain value

### T-11 — Create `mobile/.env` `[DEVOPS]`
**Status**: [x] Done — 2026-04-10  
**Depends On**: T-10 (need Cognito domain value)  
- [x] Create `mobile/.env` with:
  - `EXPO_PUBLIC_API_BASE_URL=https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com`
  - `EXPO_PUBLIC_COGNITO_CLIENT_ID=4dqle0d1u53tudl6lg7rfmbbgp`
  - `EXPO_PUBLIC_COGNITO_DOMAIN=https://ai-assistant-dev.auth.us-east-1.amazoncognito.com`
- [x] Confirm file is gitignored

### T-12 — Mock-Mode Smoke Test (Mobile → Lambda) `[QA]`
**Status**: [x] Done — 2026-04-19 (completed as part of T-17 Stage 4 sign-off)  
**Depends On**: T-10, T-11  
- [x] Run Expo app against dev API
- [x] Complete Cognito sign-in via hosted UI
- [x] Send a chat request — confirm mock response returns
- [x] Trigger a write proposal — confirm proposal card renders
- [x] Approve proposal — confirm execution response
- [x] Reject proposal — confirm rejection path
- [x] Update `test-signoff.md` with results

---

## Phase 10 — Live Provider Integration `[DEVOPS]` `[QA]`
> Second half of Stage 4. Blocked on Eric providing credentials.

### T-13 — Eric Provides Live Provider Credentials `[HUMAN]`
**Status**: [x] Done — credentials confirmed in `backend/.env.local`  
**Depends On**: —  
- [x] Google OAuth credentials (client ID + secret) — present in .env.local
- [x] Microsoft OAuth credentials (client ID + secret) — present in .env.local
- [x] Plaid credentials (client ID + secret, sandbox env) — present in .env.local

### T-14 — Populate Secrets Manager with Provider Credentials `[DEVOPS]`
**Status**: [x] Done — 2026-04-10  
**Depends On**: T-13  
- [x] Populate `GOOGLE_OAUTH_SECRET_ARN` secret in AWS Secrets Manager (dev)
- [x] Populate `MICROSOFT_OAUTH_SECRET_ARN` secret in AWS Secrets Manager (dev)
- [x] Populate `PLAID_SECRET_ARN` secret in AWS Secrets Manager (dev)
- [x] Confirm all secrets are KMS-encrypted (project CMK `alias/ai-assistant-dev`)

### T-15 — Redeploy Lambda in Live Provider Mode `[DEVOPS]`
**Status**: [x] Done — 2026-04-11  
**Depends On**: T-14  
- [x] Update `mock_provider_mode = false` in `terraform/environments/dev/terraform.tfvars`
- [x] Set GitHub Actions variable `MOCK_PROVIDER_MODE=false` in `dev` environment
- [x] Push to `main` → CI/CD redeploys Lambda
- [x] Confirm deployment succeeds
- [x] Update `deployment-log.md`

### T-16 — Provider OAuth Flows (Google + Microsoft) `[QA]`
**Status**: [x] Done — 2026-04-18 (signed off in test-signoff.md)  
**Depends On**: T-15  
- [x] Run `scripts/start-provider-auth.ps1` — Google OAuth flow end-to-end
- [x] Run `scripts/start-provider-auth.ps1` — Microsoft OAuth flow end-to-end
- [x] Confirm tokens stored correctly in dev store (DynamoDB `ai-assistant-dev-tokens`)

### T-17 — Full Live End-to-End Test `[QA]`
**Status**: [x] Done — 2026-04-19 (Stage 4 QA gate cleared)  
**Depends On**: T-16  
- [x] Google Calendar read via mobile chat
- [x] Google Tasks read and create_task
- [x] Google Drive document fetch (meeting prep intent)
- [x] Microsoft Calendar read
- [x] Microsoft To Do read and create_task
- [x] Plaid sandbox account/balance read
- [x] Prompt regression suite against live dev endpoint
- [x] Confirm no provider tokens visible in CloudWatch logs
- [x] **QA sign-off in `test-signoff.md`** — Stage 4 gate

---

## Phase 11 — Staging Pipeline `[DEVOPS]` `[QA]`
> **Stage 5 → Stage 6**. Do not begin until T-17 QA sign-off is complete.

### T-18 — Staging CI/CD Pipeline `[DEVOPS]`
**Status**: [x] Done — 2026-04-19 (PR #29 merged)  
**Depends On**: T-17 (Stage 4 QA sign-off)  
- [x] Create `.github/workflows/deploy-staging.yml` — triggers on `v*` tags
- [x] Refactor `deploy-dev.yml`: move `mock_provider_mode` to a GitHub Actions variable (not hardcoded)
- [ ] Create staging IAM deploy role in AWS — **HUMAN (Eric)** — required before T-19
- [ ] Create staging S3 Terraform state bucket — handled by `ericreilly999-ai-assistant-tfstate` bucket (shared with dev)
- [ ] Add `staging` GitHub environment with secrets/variables — **HUMAN (Eric)** — required before T-19
- [x] Create `terraform/environments/staging/` config

### T-19 — Deploy to Staging `[DEVOPS]`
**Status**: [ ] Pending  
**Depends On**: T-18  
- [ ] Tag release candidate: `git tag v1.0.0-rc1`
- [ ] Confirm staging pipeline deploys successfully
- [ ] Smoke test staging `/health` endpoint
- [ ] Update `deployment-log.md`

### T-20 — Full QA Validation on Staging `[QA]`
**Status**: [ ] Pending  
**Depends On**: T-19  
- [ ] Repeat full live provider test suite against staging endpoint
- [ ] Confirm all smoke tests pass
- [ ] **QA sign-off in `test-signoff.md`** — Stage 6 gate (final gate before prod)

---

## Phase 12 — Production Deployment `[HUMAN]` `[DEVOPS]` `[QA]`
> **Stage 7**. Requires explicit human approval before any action.

### T-21 — Human Approval for Production `[HUMAN]`
**Status**: [ ] Pending  
**Depends On**: T-20 (Stage 6 QA sign-off)  
⚠️ Project Manager will surface a production readiness summary to Eric before proceeding. No deployment action taken until Eric explicitly approves.

### T-22 — Deploy to Production `[DEVOPS]`
**Status**: [ ] Pending  
**Depends On**: T-21  
- [ ] Create `terraform/environments/prod/` config
- [ ] Tag production release: `git tag v1.0.0`
- [ ] Deploy via manually triggered GitHub Action (prod environment)
- [ ] Confirm production smoke tests pass
- [ ] Update `deployment-log.md`

### T-23 — Production Smoke Test Sign-Off `[QA]`
**Status**: [ ] Pending  
**Depends On**: T-22  
- [ ] `/health` returns 200 on prod endpoint
- [ ] End-to-end smoke test (read-only) on production
- [ ] Confirm alarms and dashboards are active
- [ ] **Final sign-off in `test-signoff.md`**
