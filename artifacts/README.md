# Artifacts Contract

Generated outputs for CI, self-test, demo, and Azure DevOps publication.

## Layout

- `artifacts/tests/`
  - `junit.xml`
  - `pytest.txt`
  - `ruff.txt`
  - `mypy.txt`
- `artifacts/selftest/`
  - `ingest/`
  - `asvs/`
  - `ssdf/`
  - `selftest_summary.md`
  - `selftest_summary.json`
- `artifacts/demo/`
  - `reqif/`
  - `selftest/`
  - `demo_summary.md`
  - `demo_summary.json`

## Notes

- These paths are intended to be stable for Azure DevOps `PublishTestResults` and `PublishPipelineArtifact` steps.
- Generated contents under `artifacts/` are ignored by git; only this README is tracked.
