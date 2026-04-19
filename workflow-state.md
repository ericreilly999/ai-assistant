# Workflow State

> Last updated: 2026-04-19 by Project Manager

## Project
**Name**: AI Assistant MVP  
**Route-to-live**: Standard (dev → staging → prod)  
**Started**: 2026-03-16

---

## Current Stage

**Stage**: 5 — Deploy to Staging  
**Status**: Blocked on Eric's manual AWS + GitHub setup (see Next Action)  
**Active agent**: None — awaiting Eric human actions before T-19 can run  
**Started**: 2026-04-19

---

## Gate Status

| Gate | Required | Status |
|------|----------|--------|
| Spec complete + TODO.md written | Stage 0 → 1 | ✅ |
| All QA test-writing tasks complete | Stage 1 → 2 | ✅ |
| All DEV tasks complete, code on main | Stage 2 → 3 | ✅ |
| Dev environment live + smoke tests pass | Stage 3 → 4 | ✅ |
| QA sign-off on dev (test-signoff.md) | Stage 4 → 5 | ✅ — T-17 signed off 2026-04-19 |
| Staging live + smoke tests pass | Stage 5 → 6 | ❌ |
| QA sign-off on staging (test-signoff.md) | Stage 6 → 7 | ❌ |
| **Human approval for production** | Stage 7 | ❌ |

---

## Next Action

**Eric (human actions required)** — complete these before T-19 (staging deploy) can run:

**In AWS Console:**
1. Create staging IAM deploy role trusted for GitHub Actions OIDC, scoped to `repo:ericreilly999/ai-assistant:environment:staging`
   - Match permissions pattern of `ai-assistant-github-actions-deploy` (dev role)
   - Suggested name: `ai-assistant-github-actions-deploy-staging`

**In GitHub (repo Settings → Environments → New environment "staging"):**
2. Create GitHub environment `staging` with the following:

| Name | Type | Value |
|------|------|-------|
| `AWS_DEPLOY_ROLE_ARN` | Secret | ARN of new staging IAM role |
| `TF_BACKEND_BUCKET` | Secret | `ericreilly999-ai-assistant-tfstate` |
| `AWS_REGION` | Variable | `us-east-1` |
| `MOCK_PROVIDER_MODE` | Variable | `false` |
| `TF_CORS_ORIGINS` | Variable | (staging domain or `"*"` for now) |
| `TF_CALLBACK_URLS` | Variable | Cognito staging callback URL |
| `TF_LOGOUT_URLS` | Variable | Cognito staging logout URL |
| `TF_BEDROCK_MODEL_ID` | Variable | `us.amazon.nova-pro-v1:0` |
| `TF_COGNITO_DOMAIN` | Variable | `ai-assistant-staging` (must be globally unique) |

**After first terraform apply:**
3. Write real OAuth credentials into staging Secrets Manager secrets (Google, Microsoft, Plaid)

**Once steps 1–2 are done**: trigger staging deploy via GitHub Actions → deploy-staging → Run workflow (push a `v*` tag or manually trigger). This runs T-19.

---

## Active Blockers

Eric's staging setup (AWS IAM role + GitHub `staging` environment). No agent action possible until these are in place.
