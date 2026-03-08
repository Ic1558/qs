# QS Operator Runbook

This runbook covers the minimum operator actions for the canonical QS module in:
- Local checkout: `/Users/icmini/0luka/repos/qs`
- GitHub: `https://github.com/Ic1558/qs`

## Startup

Bootstrap a clean local run:

```bash
cd /Users/icmini/0luka/repos/qs
zsh tools/bootstrap.zsh
```

Useful bootstrap switches:

```bash
NO_START=1 zsh tools/bootstrap.zsh
SKIP_TESTS=1 zsh tools/bootstrap.zsh
PORT=7085 zsh tools/bootstrap.zsh
```

Production steady-state should use `launchd`, not a foreground bootstrap shell.

## Service Checks

Confirm the module registry and runtime surface:

```bash
cd /Users/icmini/0luka
python3 core_brain/ops/modulectl.py validate
python3 core_brain/ops/modulectl.py status universal_qs_api
curl -s http://127.0.0.1:7084/api/health
```

Expected:
- registry is valid
- `com.0luka.universal-qs-api` resolves to `repos/qs`
- health reports `status: ok`

## Acceptance Block Handling

Inspect acceptance for a project:

```bash
cd /Users/icmini/0luka/repos/qs
PYTHONPATH=src python3 -m universal_qs_engine.cli project-acceptance --project-id <project_id>
```

Apply an acceptance override:

```bash
cd /Users/icmini/0luka/repos/qs
PYTHONPATH=src python3 -m universal_qs_engine.cli project-acceptance-override \
  --project-id <project_id> \
  --author <operator_name> \
  --justification "Approved for owner export after manual review"
```

Important:
- acceptance override only clears the acceptance gate
- it does not clear unresolved `block_owner` review flags

## Review Flag Handling

Add an acknowledgement note to a review flag:

```bash
cd /Users/icmini/0luka/repos/qs
PYTHONPATH=src python3 -m universal_qs_engine.cli project-review-ack \
  --project-id <project_id> \
  --flag-id <flag_id> \
  --comment "Reviewed by QS operator"
```

Important:
- `ack_note` does not unblock `block_owner`
- it is for audit trail only

Resolve a dimensional review flag with a deterministic override:

```bash
cd /Users/icmini/0luka/repos/qs
PYTHONPATH=src python3 -m universal_qs_engine.cli project-review-override \
  --project-id <project_id> \
  --segment-id <segment_id> \
  --field depth \
  --value 0.45 \
  --flag-id <flag_id> \
  --justification "Measured from structural section S-04"
```

After a segment override, rebuild/export flows will use:
- `basis_status = MANUAL_ALLOWANCE`
- override note in the audit trail

## Manual Cleanup

Uploaded working files live under:
- `/Users/icmini/0luka/repos/qs/tmp/job_*`

Project state lives under:
- `/Users/icmini/0luka/repos/qs/outputs/projects/<project_id>/project.json`

Generated workbooks live under:
- `/Users/icmini/0luka/repos/qs/outputs`

Remove stale upload jobs:

```bash
find /Users/icmini/0luka/repos/qs/tmp -mindepth 1 -maxdepth 1 -type d -name 'job_*' -exec rm -rf {} +
```

Do not delete `outputs/projects/<project_id>` unless you intend to remove project state.

## DENSITY_FALLBACK Interpretation

`DENSITY_FALLBACK` means the engine could not close a quantity from deterministic geometry alone and used a fallback basis.

Operational meaning:
- internal trace workbook may continue
- owner export must remain blocked until the issue is resolved

Typical resolution path:
1. inspect the trace workbook and find the affected segment/component
2. confirm the missing dimension or source basis
3. apply `project-review-override` with a measured value and justification
4. rerun acceptance/export

If `DENSITY_FALLBACK` remains unresolved, treat the project as not owner-ready.

## Export Recheck

Run the guarded export path:

```bash
cd /Users/icmini/0luka/repos/qs
PYTHONPATH=src python3 -m universal_qs_engine.cli generate-boq --project-id <project_id>
```

Expected:
- exit `0` when owner export is allowed
- exit `2` when blocked by review or acceptance gates
- internal trace workbook still generated for audit
