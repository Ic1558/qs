# VERIFY

- `PYTHONPATH=src:/Users/icmini/0luka/tools python3 -m pytest -q tests/test_authoring_flow.py tests/test_discipline_aggregation.py`
  - Expected: `24 passed`
- `python3 verify_phase6_proof.py`
  - Expected:
    - internal workbook exports successfully
    - owner export blocks before acceptance override
    - owner export succeeds after override

## Notes

- The verification command includes `/Users/icmini/0luka/tools` so `qs_engine` resolves from the monorepo tool checkout.
- This PR intentionally does not verify HTTP `service.py` routes; those belong to the follow-up API/UI slice.
