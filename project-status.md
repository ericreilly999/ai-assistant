# AI Assistant — Project Status

Last updated: 2026-04-08

---

## Session Roles
- **Cowork (this session)** — planning, status tracking, task layout, AWS inspection, credential loading
- **Claude Code** — all file creation, code changes, git commits, Terraform runs, deployments

---

## Current Phase
**Live integration, Lambda deployment, and first end-to-end test**

All 9 development phases (backend, infra, mobile, tests) are code-complete and merged to `main`. The work remaining is operational: deploying the Lambda, loading credentials into AWS, and doing a real end-to-end run through the mobile app.

---

## Workflow
- **Planning / status / AWS inspection / file management**: Eric uses Cowork (Claude desktop)
- **Active coding, testing, git push, Lambda deploy**: Eric uses **Claude Code** directly in the terminal inside the repo (`cd C:\dev\gitrepos\ai-assistant-main\ai-assistant && claude`)
- This file is the shared source of truth between both sessions

---

## Deployed AWS Infrastructure (dev)

| Resource | Value |
|---|---|
| Cognito User Pool ID | `us-east-1_fo4459oxO` |
| Cognito App Client ID | `4dqle0d1u53tudl6lg7rfmbbgp` |
| API Gateway Endpoint | `https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com` |
| Lambda Function | ❌ Not yet deployed |
| Secrets Manager (Google) | ❌ Not yet created |
| Secrets Manager (Microsoft) | ❌ Not yet created |
| Secrets Manager (Plaid) | ❌ Not yet created |
| Cognito Hosted UI Domain | ❌ Not yet configured |

---

## Current Blockers (waiting on Eric)

### 1. Google OAuth Credentials
- Where to find: [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
- Find the OAuth 2.0 client created for this project
- Need: **Client ID** and **Client Secret**
- Redirect URI that must be registered: `http://localhost:8787/oauth/google/callback`
- Scopes needed: `calendar`, `tasks`, `drive.readonly`

### 2. Microsoft OAuth Credentials
- Where to find: [portal.azure.com](https://portal.azure.com) → App registrations
- Find the ai-assistant app registration
- Need: **Application (client) ID** and a **Client Secret** (from "Certificates & secrets")
- Redirect URI that must be registered: `http://localhost:8787/oauth/microsoft/callback`
- Scopes needed: `Calendars.ReadWrite`, `Tasks.ReadWrite`, `offline_access`

### 3. Plaid Credentials
- Where to find: [dashboard.plaid.com/developers/keys](https://dashboard.plaid.com/developers/keys)
- Need: **Client ID** and **Sandbox Secret**

Once Eric provides these, the next steps below can be completed by Claude Code without further input.

---

## Next Steps (in order)

### Stage 1 — Deploy in mock mode (nearly unblocked — one GitHub setup step needed)

**Deployment is via CI/CD — push to `main` triggers automatic deploy. No manual Terraform needed.**

Pipeline: `.github/workflows/deploy-dev.yml` — runs tests → typecheck → terraform validate → `terraform apply`

AWS prerequisites already in place:
- ✅ GitHub Actions OIDC provider: `arn:aws:iam::290993374431:oidc-provider/token.actions.githubusercontent.com`
- ✅ IAM deploy role: `arn:aws:iam::290993374431:role/ai-assistant-github-actions-deploy`
- ✅ Lambda execution role: `arn:aws:iam::290993374431:role/ai-assistant-dev-orchestrator-role`
- ✅ S3 state bucket: `ericreilly999-ai-assistant-tfstate`

Missing — set these in GitHub → Settings → Environments → dev → Secrets:
- [ ] `AWS_DEPLOY_ROLE_ARN` = `arn:aws:iam::290993374431:role/ai-assistant-github-actions-deploy`
- [ ] `TF_BACKEND_BUCKET` = `ericreilly999-ai-assistant-tfstate`

Once secrets are set:
- [ ] Push to `main` → pipeline deploys Lambda automatically (mock mode, no credentials needed)
- [ ] Smoke test `/health` on `https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com`
- [ ] Create `mobile/.env` (values known — Cowork can create this now):
  - `EXPO_PUBLIC_API_BASE_URL=https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com`
  - `EXPO_PUBLIC_COGNITO_CLIENT_ID=4dqle0d1u53tudl6lg7rfmbbgp`
  - `EXPO_PUBLIC_COGNITO_DOMAIN=` (TBD — Cognito hosted UI domain not yet configured)
- [ ] Configure Cognito hosted UI domain (needed for mobile sign-in flow)
- [ ] Run Expo app and do first full UI test in mock mode (mobile → API Gateway → Lambda → mock responses)

Note: `backend/.env.local` is gitignored and for local dev only — it does not affect CI/CD.

### Stage 1b — Staging pipeline (DEFERRED — do not execute until dev is fully verified)
- [ ] Create `.github/workflows/deploy-staging.yml` — triggers on `v*` tags (e.g. `v1.0.0-rc1`)
  - Same structure as `deploy-dev.yml` but targets `staging` environment and uses `mock_provider_mode = false`
  - Needs a `staging` GitHub environment with its own `AWS_DEPLOY_ROLE_ARN` and `TF_BACKEND_BUCKET` secrets
  - Staging IAM deploy role and S3 state bucket do not yet exist in AWS — need to be created
  - Note: `deploy-dev.yml` currently hardcodes `mock_provider_mode = true` — should be a GitHub var, not hardcoded
  - **⛔ Do not build or trigger this until Stage 1 (dev) and Stage 2 (live providers on dev) are fully working**

### Stage 2 — Live provider testing (blocked on Eric providing credentials)
- [ ] **Eric provides credentials** (Google, Microsoft, Plaid) — see blockers above
- [ ] Populate Secrets Manager with real credential values (Cowork can do this)
- [ ] Redeploy with `mock_provider_mode = false` via `terraform apply`
- [ ] Run `scripts/start-provider-auth.ps1` to walk through Google + Microsoft OAuth flows
- [ ] Verify all 8 Phase 2 checklist items in `TODO.md`
- [ ] First full live end-to-end test: mobile app → API Gateway → Lambda → real provider

---

## What's Complete

- ✅ Phase 1 — Housekeeping / env / CORS fixes
- ✅ Phase 2 — Provider integration code (Google Calendar, Tasks, Drive; Microsoft Calendar, Todo; Plaid) — **code complete, not live-verified**
- ✅ Phase 3 — Orchestrator (intent classification, dynamic risk, structured logging)
- ✅ Phase 4 — Test suite (122 tests passing)
- ✅ Phase 5 — Bedrock integration (Converse API, guardrails)
- ✅ Phase 6 — AWS infrastructure (Secrets Manager, KMS, Lambda alias, ACM, Route53, Cognito, observability alarms)
- ✅ Phase 7 — Mobile app (Cognito auth, proposal UI, error handling, conversation history, unit tests)
- ✅ Phase 8 — Prompt regression tests
- ✅ Phase 9 — Python 3.10 compatibility fix

---

## Known Issues

- **Local git repo (`ai-assistant/`)** has a corrupted state from an interrupted cherry-pick. Use the fresh clone at `ai-assistant-main/` instead. If you want to fix the old one: `git cherry-pick --abort` in that directory.
- **Lambda has never been deployed** — the API Gateway exists but has no integration target yet.
- **Secrets Manager is empty** for this project — the Terraform module for secrets was written but `terraform apply` either wasn't run or didn't include the secret values.
- **Cognito hosted UI domain** is not configured, which blocks the mobile OAuth sign-in flow.
