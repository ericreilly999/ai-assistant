# Terraform

This directory contains reusable Terraform modules plus environment roots for:

- `dev`
- `staging`
- `prod`

## Validation

Use `scripts/validate-terraform.ps1` once Terraform is installed locally.

## Packaging

Each environment root uses the `archive` provider to package the Lambda source from `backend/src` into a deployable zip.