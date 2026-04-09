# CI/CD Pipeline

The CI/CD pipeline uses GitHub Actions. Workflows live in `.github/workflows/`.

## Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Releasable code — every merge auto-deploys to `dev` |
| Feature branches | Short-lived; branched from `main`, merged via PR |
| Release tags (`v*`) | Trigger `staging` deploy and manual `prod` approval gate |

**Never push directly to `main`.** All changes go through a pull request with passing CI.

## Pull Request Checks

All of the following must pass before a PR can merge:

| Check | Command |
|---|---|
| Backend lint | `ruff check src/ tests/` |
| Backend type check | `mypy src/` |
| Backend unit tests | `python -m unittest discover -s tests -t .` |
| Mobile lint | `npm run lint` (inside `mobile/`) |
| Mobile unit tests | `npm test` (inside `mobile/`) |
| Terraform fmt | `terraform fmt -check -recursive` |
| Terraform validate | `terraform validate` (all three environments) |
| tflint | `tflint --recursive` |
| Security scan | `tfsec terraform/` or `checkov -d terraform/` |
| Lambda build | `.\scripts\package-lambda.ps1` + artifact size check |

## Deployment Jobs

### dev (automatic on `main` merge)

1. All PR checks pass (already validated).
2. Package Lambda artifact.
3. Run `terraform apply` on `terraform/environments/dev`.
4. Validate Lambda alias update.
5. Run smoke test against `dev` API endpoint.

### staging (on release candidate tag)

Triggered by pushing a tag matching `v*-rc*` (e.g. `v1.0.0-rc1`).

1. All PR checks.
2. Package Lambda artifact.
3. Run `terraform apply` on `terraform/environments/staging`.
4. Run automated smoke tests (see below).

### prod (manual approval)

Triggered after `staging` is green and a production release tag is pushed (e.g. `v1.0.0`).

1. Manual approval required in GitHub Actions.
2. Package Lambda artifact (same artifact as staging if possible).
3. Run `terraform apply` on `terraform/environments/prod`.
4. Validate Lambda alias update.

## Staging Smoke Tests

The staging smoke test suite runs automatically after every staging deploy:

1. Sign in with a test user.
2. Connect sandbox/test providers.
3. Ask a read-only calendar question → verify response.
4. Generate a grocery list write proposal → verify proposal structure.
5. Approve and execute a non-destructive test write.
6. Fetch a Google Drive document summary → verify summary content.

All smoke tests must pass for the staging deploy to be considered successful.

## Rollback Procedure

### Lambda rollback

In the CI workflow, every Lambda apply publishes a new version and shifts an alias. To roll back, re-run the previous successful deploy job with the previous artifact version, or:

```bash
aws lambda update-alias \
  --function-name ai-assistant-orchestrator-prod \
  --name live \
  --function-version <previous-version>
```

### Mobile rollback

- iOS: revert through App Store Connect to the previous approved build.
- Android: revert through Google Play Console to the previous release.

## Secrets in CI

GitHub Actions secrets (not committed to the repo) hold:

| Secret name | Purpose |
|---|---|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Terraform and Lambda deploy (per environment) |
| `AWS_REGION` | Target region |
| `TF_VAR_*` overrides | Any Terraform variables that must not appear in tfvars files |

Use environment-scoped secrets in GitHub to prevent `dev` credentials from being used in `prod` workflows.

## Definition of Done for a Release

A release is ready for `prod` when:

- [ ] Mobile apps are functional in `dev` and `staging`.
- [ ] Terraform can provision from clean state in all environments.
- [ ] All six provider integrations are functional within MVP scope.
- [ ] No write executes without explicit user approval.
- [ ] No application database is in use.
- [ ] Unit, contract, prompt regression, and smoke tests pass in CI.
- [ ] Production alarms and dashboards are active.
- [ ] Secrets and tokens are confirmed redacted from CloudWatch logs.
