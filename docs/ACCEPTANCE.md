# Acceptance

Final gate criteria encoded in this scaffold:

- PO-4 / PO-5 / PO-6 reconciliation must pass.
- Symbol recognition confidence must be at least `0.95`.
- PDF vs DWG parity delta must be below `1%`.
- All audit links must resolve.
- Standard-plan runtime must stay below `5` minutes.

The check is available through `/api/v1/acceptance/evaluate`.
