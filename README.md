# AI Assistant MVP Scaffold

This repository contains a development-ready scaffold for the personal assistant MVP described in the specification at `docs/assistant-mvp-spec.md`.

## What Is Included

- AWS Lambda backend scaffold in `backend/`
- Mock-provider capable orchestration flow for local and early dev validation
- Terraform scaffolding for `dev`, `staging`, and `prod` in `terraform/`
- React Native / Expo mobile shell in `mobile/`
- PowerShell helper scripts in `scripts/`
- GitHub Actions CI scaffold in `.github/workflows/`

## Current Behavior

The backend is intentionally configured for `MOCK_PROVIDER_MODE=true` by default. That means:

- the Lambda can be packaged and deployed into a development environment before live provider secrets are available
- provider adapters expose normalization logic and fixture-backed mock data
- unit and contract tests can run without real cloud credentials

## Recommended Local Commands

- `scripts/run-backend-tests.ps1`
- `scripts/test-integrations.ps1`
- `scripts/package-lambda.ps1`
- `scripts/validate-terraform.ps1`

## Notes

- No deployments are performed by this scaffold.
- Live Google, Microsoft, and Plaid transport wiring is intentionally kept behind adapter interfaces so development can start immediately in mock mode.
- Bedrock identifiers are injected through Terraform variables and Lambda environment variables.