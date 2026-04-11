# Deployment Log — AI Assistant MVP

> Maintained by: DevOps Engineer  
> Updated after every environment deployment

---

## Dev Environment

### Deploy #1 — Initial Lambda Deploy (Mock Mode)
**Date**: ~2026-04-08  
**Environment**: dev  
**Triggered by**: Push to `main` → CI/CD pipeline (`.github/workflows/deploy-dev.yml`)  
**Deployed by**: GitHub Actions (OIDC → IAM role `ai-assistant-github-actions-deploy`)  
**Artifact**: Lambda package built from `backend/` — Python 3.10  
**Config**: `MOCK_PROVIDER_MODE=true`  
**Result**: ✅ Success  

**Deployed Infrastructure:**

| Resource | Value |
|---|---|
| API Gateway Endpoint | `https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com` |
| Lambda Function | `ai-assistant-dev-orchestrator` |
| Lambda Alias | `live` |
| Cognito User Pool | `us-east-1_fo4459oxO` |
| Cognito App Client | `4dqle0d1u53tudl6lg7rfmbbgp` |
| Cognito Hosted UI Domain | `https://ai-assistant-dev.auth.us-east-1.amazoncognito.com` (provisioned via CI — Deploy #2) |
| Secrets Manager (Google) | ✅ Populated — KMS encrypted (see Deploy #3) |
| Secrets Manager (Microsoft) | ✅ Populated — KMS encrypted (see Deploy #3) |
| Secrets Manager (Plaid) | ✅ Populated — KMS encrypted (see Deploy #3) |
| KMS Key | ✅ Created |
| CloudWatch Alarms | ✅ Active |
| CloudWatch Dashboard | ✅ Active |

**Smoke Test**: `/health` endpoint confirmed responding at `https://lbg6dypkqi.execute-api.us-east-1.amazonaws.com/dev/health`  
**Notes**: Deployed in mock mode. Live provider secrets not yet populated. Cognito hosted UI domain not yet configured — blocks mobile OAuth flow.

---

### Deploy #2 — Cognito Hosted UI Domain
**Date**: 2026-04-10  
**Environment**: dev  
**Triggered by**: Push to `main` → CI/CD pipeline (`.github/workflows/deploy-dev.yml`)  
**Deployed by**: GitHub Actions (OIDC → IAM role `ai-assistant-github-actions-deploy`)  
**Change**: Enabled Cognito hosted UI prefix domain `ai-assistant-dev` via `aws_cognito_user_pool_domain`  
**Result**: ✅ Success — applied directly via `terraform apply` on 2026-04-10; hosted UI confirmed reachable (HTTP 302)

**Cognito Hosted UI:**

| Resource | Value |
|---|---|
| Cognito Hosted UI Domain | `https://ai-assistant-dev.auth.us-east-1.amazoncognito.com` |
| Authorization endpoint | `https://ai-assistant-dev.auth.us-east-1.amazoncognito.com/oauth2/authorize` |
| Token endpoint | `https://ai-assistant-dev.auth.us-east-1.amazoncognito.com/oauth2/token` |

**Notes**: Domain prefix `ai-assistant-dev` provisioned as a Cognito-managed prefix domain (no custom domain / ACM cert required for dev). The `cognito_domain` variable is now threaded from the CI workflow → `terraform.tfvars` → dev `module "auth"` → the existing `aws_cognito_user_pool_domain` resource in the `cognito_user_pool` module.

---

### Deploy #3 — Secrets Manager Population + CMK KMS Encryption
**Date**: 2026-04-10  
**Environment**: dev  
**Triggered by**: Manual `aws secretsmanager put-secret-value` + `terraform apply`  
**Change**: Populated all three provider secrets with live credentials and attached project CMK to each secret  
**Result**: ✅ Success

**Secrets Manager:**

| Secret Path | ARN | KMS Key |
|---|---|---|
| `ai-assistant-dev/google-oauth` | `arn:aws:secretsmanager:us-east-1:290993374431:secret:ai-assistant-dev/google-oauth-wUoySm` | `alias/ai-assistant-dev` (CMK) |
| `ai-assistant-dev/microsoft-oauth` | `arn:aws:secretsmanager:us-east-1:290993374431:secret:ai-assistant-dev/microsoft-oauth-zOJ4Uj` | `alias/ai-assistant-dev` (CMK) |
| `ai-assistant-dev/plaid` | `arn:aws:secretsmanager:us-east-1:290993374431:secret:ai-assistant-dev/plaid-J3j6Dq` | `alias/ai-assistant-dev` (CMK) |

**Secret Key Structure** (JSON keys per secret):
- `google-oauth`: `google-client-id`, `google-client-secret`
- `microsoft-oauth`: `microsoft-client-id`, `microsoft-client-secret`
- `plaid`: `plaid-client-id`, `plaid-secret`

**Terraform Changes**: Added `kms_key_arn` variable to `secrets_bundle` module; wired `module.kms.key_arn` through `main.tf`.  
**Notes**: Initial placeholder values (written by Terraform) were overwritten with live credentials. All secrets are now CMK-encrypted. `mobile/.env` created with Cognito domain. Next step: T-15 — redeploy Lambda with `mock_provider_mode=false`.

---

### Deploy #4 — Live Provider Mode Enable
**Date**: 2026-04-11  
**Environment**: dev  
**Triggered by**: Push to `main` → CI/CD pipeline (`.github/workflows/deploy-dev.yml`)  
**Deployed by**: GitHub Actions (OIDC → IAM role `ai-assistant-github-actions-deploy`)  
**Change**: `mock_provider_mode=false` — Lambda now calls real providers (Google OAuth, Microsoft OAuth, Plaid)  
**GitHub Actions variable**: `MOCK_PROVIDER_MODE=false` set in `dev` environment  
**Result**: ✅ Success — CI run confirmed, Lambda env var `MOCK_PROVIDER_MODE=false`, `/health` returns HTTP 200  

**Config change:**

| Variable | Before | After |
|---|---|---|
| `MOCK_PROVIDER_MODE` | `true` | `false` |

**Notes**: T-15 complete. Lambda is now wired to live provider secrets in Secrets Manager. Enables T-16 (OAuth flows) and T-17 (full live end-to-end test).

---

### Deploy #5 — Cognito Callback URLs + IAM Fix
**Date**: 2026-04-11  
**Environment**: dev  
**Triggered by**: Push to `main` → CI/CD pipeline (`.github/workflows/deploy-dev.yml`)  
**Deployed by**: GitHub Actions (OIDC → IAM role `ai-assistant-github-actions-deploy`)  
**Change**: Registered Expo Go redirect URIs in Cognito app client (`callback_urls` and `logout_urls`). Also fixed IAM deploy role: added `CognitoDomain` statement scoping domain actions to resource `*` (required by AWS — domain actions cannot be scoped to `userpool/*` ARN).  
**Result**: ✅ Success — Terraform apply succeeded, smoke tests pass  

**GitHub Actions variables set:**

| Variable | Value |
|---|---|
| `TF_CALLBACK_URLS` | `"exp://localhost:8081", "exp://127.0.0.1:8081", "exp://10.0.2.2:8081", "exp://localhost:8081/--/", "exp://127.0.0.1:8081/--/", "exp://10.0.2.2:8081/--/"` |
| `TF_LOGOUT_URLS` | `"exp://localhost:8081", "exp://127.0.0.1:8081", "exp://10.0.2.2:8081"` |

**Cognito App Client Callback URLs now registered:**
- `exp://localhost:8081` and `exp://localhost:8081/--/`
- `exp://127.0.0.1:8081` and `exp://127.0.0.1:8081/--/`
- `exp://10.0.2.2:8081` and `exp://10.0.2.2:8081/--/`

**Notes**: T-12 Cognito blocker fully resolved. Eric can now run the T-12 manual smoke test. Steps in `test-signoff.md` — Phase 4.

---

## Staging Environment

**Status**: ❌ Not yet deployed  
**Blocked on**: Dev Stage 4 QA sign-off

---

## Production Environment

**Status**: ❌ Not yet deployed  
**Blocked on**: Staging Stage 6 QA sign-off + explicit human approval
