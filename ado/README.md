# Azure DevOps Support

This folder contains Azure Pipeline templates for CI, self-test, and demo deployment.

## Files

- `templates/ci.yml`
  - Python toolchain bootstrap
  - `uv sync`
  - lint, typecheck, pytest JUnit output
  - publish `artifacts/tests`
- `templates/selftest.yml`
  - build stable self-test and demo artifacts
  - publish `artifacts/selftest` and `artifacts/demo`
- `templates/deploy-container-app.yml`
  - deploy or update the demo container app through Azure CLI and Bicep

## Root Pipeline

- `azure-pipelines.yml`
  - `ci`
  - `selftest`
  - `image`
  - `deploy_demo`
  - `smoke_demo`

## Required Variables

Set these in Azure DevOps before enabling deploy stages:

- `azureServiceConnection`
- `azureResourceGroup`
- `azureLocation`
- `acrName`
- `containerAppEnvironmentName`
- `containerAppName`

If `azureServiceConnection` is left empty, the deploy stages are skipped and the pipeline acts as CI plus self-test only.
