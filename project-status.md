# Project Status — integreat

> Last updated: 2026-04-19

## Summary

Stage 4 QA (dev) is signed off. T-18 complete — staging CI/CD pipeline merged (PR #29). Param guard fixes merged (PRs #27, #28). A backend.hcl gitignore cleanup is in flight. **Eric's action required before T-19 (first staging deploy) can run** — see below.

## What We Just Completed

- 2026-04-19 — **T-18 COMPLETE** — staging CI/CD pipeline merged (PR #29, `deploy-staging.yml`) ✅
- 2026-04-19 — PR #28 merged: param guards for Google Calendar + Plaid transactions dev routes
- 2026-04-19 — PR #27 merged: param guard for Microsoft calendar dev route
- 2026-04-19 — **T-17 SIGNED OFF** — Stage 4 QA complete ✅
- 2026-04-19 — T-16 SIGNED OFF — OAuth tokens stored in DynamoDB, providers connected ✅
- 2026-04-19 — PRs #23–26 merged: DynamoDB token store (infra + impl), Checkov cleanup, lint fix

## What's In Progress

- DevOps: backend.hcl gitignore cleanup PR (in progress)

## What's Coming Next — Human Actions Required Before T-19

⚠️ Before the first staging deploy can run, Eric needs to complete:

**In AWS:**
1. Create a staging IAM deploy role trusted for GitHub Actions OIDC, scoped to `repo:ericreilly999/ai-assistant:environment:staging`
   - Same permissions pattern as `ai-assistant-github-actions-deploy` (dev role)
   - Role name suggestion: `ai-assistant-github-actions-deploy-staging`

**In GitHub (repo Settings → Environments → New environment "staging"):**
2. Create GitHub environment `staging` with:

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

Once items 1–2 are done, trigger the staging deploy via GitHub Actions → deploy-staging → Run workflow.

## Blockers

Waiting on Eric's staging setup actions (listed above) before T-19 can proceed.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `ai-assistant-staging` Cognito domain prefix taken globally | L | L | Try it — if taken, choose alternate prefix and update `TF_COGNITO_DOMAIN` |
| Staging Secrets Manager populated with wrong/empty credentials | M | H | Must write real creds post-apply before OAuth flows work in staging |
| Chat intent tests unverifiable without CI Cognito account | M | M | Manual test via Eric; CI account tracked as T-27 |
| DynamoDB root-level resource → extract to module | L | L | Pre-staging tech debt — acceptable, tracked |
