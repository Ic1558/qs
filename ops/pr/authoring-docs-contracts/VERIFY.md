# VERIFY

- `git -C /tmp/qs-authoring-docs-contracts diff --name-only origin/main...HEAD`
  - Expected changed files:
    - `docs/ACCEPTANCE.md`
    - `docs/ARCHITECTURE.md`
    - `docs/AR_MEMBER_MODEL.md`
    - `ops/pr/authoring-docs-contracts/PLAN.md`
    - `ops/pr/authoring-docs-contracts/DIFF.md`
    - `ops/pr/authoring-docs-contracts/VERIFY.md`
    - `ops/pr/authoring-docs-contracts/PR_BODY.md`
- `git -C /tmp/qs-authoring-docs-contracts diff --check origin/main...HEAD`
  - Expected: no whitespace/errors

## Scope Verification

`pyproject.toml` remains excluded because its dependency change is separable from these docs and is not required to publish the contract text itself.
