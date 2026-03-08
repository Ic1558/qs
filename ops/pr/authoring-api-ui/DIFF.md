# DIFF

- extended `src/universal_qs_engine/service.py` with:
  - `/api/v2/projects` route handling
  - project GET/PATCH dispatch
  - takeoff/review/acceptance/export route wiring
  - health payload updates for the v2 surface
- replaced the static UI files with the local-first authoring workspace:
  - `src/universal_qs_engine/ui/index.html`
  - `src/universal_qs_engine/ui/app.js`
  - `src/universal_qs_engine/ui/styles.css`
- added `tests/test_service_authoring_api.py` to cover service-level routing and static UI delivery in-process
