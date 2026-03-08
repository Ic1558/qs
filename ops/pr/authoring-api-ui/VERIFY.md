# VERIFY

- `PYTHONPATH=src:/Users/icmini/0luka/tools python3 -m pytest -q tests/test_service.py tests/test_service_authoring_api.py`
  - Expected: `15 passed`
- `PYTHONPATH=src:/Users/icmini/0luka/tools python3 -m pytest -q tests/test_authoring_flow.py tests/test_discipline_aggregation.py`
  - Expected: `24 passed`

## Notes

- Service regression uses an in-memory `RequestHandler` harness because sandboxed test execution in this environment cannot bind ephemeral ports.
- This PR depends on the authoring-core branch for the imported project API functions.
