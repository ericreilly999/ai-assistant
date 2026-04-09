# Running Tests

The project has multiple test layers. Run them in order — unit tests first, then lint/type check, then integration tests.

## Backend Unit Tests

Runs all tests under `backend/tests/` using Python's `unittest` runner.

```powershell
cd ai-assistant
.\scripts\run-backend-tests.ps1
```

### Test Modules

| File | What it covers |
|---|---|
| `test_handler.py` | Route dispatch, CORS, OPTIONS, 404, 502, all intent plan routes |
| `test_orchestrator.py` | Meeting prep (live + mock), execute edge cases, window-finding, provider error paths |
| `test_oauth.py` | Code exchange, token refresh, state mismatch, missing env var |
| `test_consent.py` | Proposal approval/rejection, expiry, missing `expires_at` |
| `test_providers.py` | HTTP-mocked live adapter methods for Google, Microsoft, Plaid |
| `test_dev_store.py` | Token read/write, clear, merge, malformed file handling |

### Running a Single Test Module

```powershell
cd ai-assistant/backend
python -m unittest tests.test_handler -v
```

### Coverage Target

The specification requires 90%+ coverage for domain, validation, and orchestration code. To measure coverage:

```bash
pip install coverage
coverage run -m unittest discover -s tests -t .
coverage report -m
```

---

## Backend Lint — ruff

```bash
cd ai-assistant/backend
# Activate venv first
ruff check src/ tests/
```

To auto-fix safe issues:

```bash
ruff check --fix src/ tests/
```

Configuration is in `backend/pyproject.toml` under `[tool.ruff]`.

---

## Backend Type Check — mypy

```bash
cd ai-assistant/backend
mypy src/
```

Configuration is in `backend/pyproject.toml` under `[tool.mypy]`. Tests are excluded from strict type checking.

---

## Integration Tests (live providers)

Requires live provider credentials to be set (see `05-provider-auth.md`).

```powershell
cd ai-assistant
.\scripts\test-integrations.ps1
```

This runs `backend.tests.test_providers` against the live adapter methods with real HTTP calls. Use `MOCK_PROVIDER_MODE=false` and have valid tokens in `backend/.local/tokens.json`.

---

## Mobile Unit Tests

```bash
cd ai-assistant/mobile
npm test
```

Uses Jest + React Native Testing Library. Tests are in `mobile/__tests__/`.

### Coverage areas

- Chat screen state transitions
- Approval modal (approve / reject)
- Token and session handling
- Provider connection state rendering
- Optimistic UI disabled for write actions until execution succeeds

---

## Terraform Validation

```powershell
cd ai-assistant
.\scripts\validate-terraform.ps1
```

This runs `terraform validate` in all three environment directories. It does not require AWS credentials — only that Terraform is initialized.

For security scanning:

```bash
# tfsec
tfsec terraform/

# checkov
checkov -d terraform/
```

---

## Prompt Regression Tests

The prompt regression suite (Phase 8) validates Bedrock intent routing and response structure against golden test cases. These require a live Bedrock configuration.

Golden cases cover:
- Schedule question
- Grocery plan
- Errand batching
- Meeting prep
- Travel planning
- Malicious prompt injection (must be blocked by guardrail)
- Write-without-consent attempt (must not execute)

Each case verifies: correct intent, no unauthorized write, valid response structure, no secret leakage.

---

## CI Pipeline Test Order

The GitHub Actions CI runs checks in this order on every pull request:

1. Backend lint (`ruff`)
2. Backend type check (`mypy`)
3. Backend unit tests
4. Mobile lint
5. Mobile unit tests
6. Terraform `fmt -check`
7. Terraform `validate`
8. `tflint`
9. `tfsec` / `checkov`
10. Lambda artifact build and validation

All checks must pass before merge to `main`.
