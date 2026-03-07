# Universal QS Engine (App Layer Plan)

## PLAN
Build a "Thinnest Viable Web App" consisting of a slim Vanilla HTML/JS/CSS frontend seamlessly integrated into the existing Python HTTP server (`service.py`).
- **Low-Cost Native**: Zero build-step frontend, entirely local/offline.
- **Workflow Pipeline**: Connects the provided API endpoints into a linear wizard for the user (Setup -> Intake -> Extract -> Review -> Output).
- **Core Principle**: Preserves the existing `universal_qs_engine` repo scaffold and acts merely as an interactive UI surface to invoke the pipeline defined in `api.py`.

## APP ARCHITECTURE
**Backend**:
- Keep using the built-in `ThreadingHTTPServer` from `src/universal_qs_engine/service.py`.
- Add a simple static file handler for `index.html`, `app.js`, and `app.css`. 
- Upgrade `api.py` and `service.py` to handle `multipart/form-data` uploads, since browser security obscures absolute file paths. Alternatively, implement a local file-picker endpoint.

**Frontend**:
- A single-page application (SPA) built with Vanilla JavaScript and Tailwind CSS (via CDN) to ensure a premium look (Glassmorphism, crisp typography) without NodeJS overhead.
- **Modules**:
  - `Drag & Drop Zone`: Handles file uploads securely.
  - `Config Panel`: Sets scales, prices, project defaults (waste, Factor F).
  - `Progress Tracker`: Visualizes the data flow from `prepare` -> `extract` -> `logic` -> `boq`.
  - `Review Queue`: Renders `low_symbol_confidence` warnings for manual checking.
  - `Output Box`: Download links for XLSX and JSON.

## FILE CHANGES
**1. Repository Updates (inside `repos/qs`)**
- `src/universal_qs_engine/service.py`: Update `do_GET` to serve static files (e.g., from `ui/`). Add a basic multipart parser in `do_POST` for `/api/v1/intake/upload`.
- `src/universal_qs_engine/ui/index.html`: The main markup entry point. Includes premium styling, dynamic layout structure.
- `src/universal_qs_engine/ui/app.js`: State machine bridging the UI clicks to the API `fetch` requests.
- `src/universal_qs_engine/ui/styles.css`: Custom animations and micro-interactions.
- `src/universal_qs_engine/api.py`: Minor augmentations to handle the new `upload` routing gracefully, routing blobs to a local `tmp/` storage which matches the local path expectation.

**2. 0Luka Core Integration (inside `0luka/core`)**
- `tools/ops/qs_launch.py`: Create a script to spin up the QS server in a background process and automatically open the default browser to `http://127.0.0.1:7084`.
- `core/health.py`: Embed the `universal_qs_engine` ping (`http://127.0.0.1:7084/api/health`) into the master health check script.

## RUNTIME/INTEGRATION
- **Execution**: The 0luka user types `AGENT_ID=gmx zsh tools/run_tool.zsh run_qs_launch`. The system starts `service.py` and pops open a Chrome window.
- **Cache Persistence**: Files uploaded via the browser get stored in an allowed path defined in `manifest.yaml` (e.g. `outputs/` or `tmp/`), maintaining strict isolation.
- **0luka Handshake**: The API responses will faithfully utilize the 0luka contract formats (`universal_qs_result_v1` and `po_workbook_bundle_v1`) defined in `contracts.py`.
- **Low-Cost Execution Mode**: Toggles for ML limits are passed through the app UI, allowing for user overrides if approved.

## VERIFY
1. **API Tests**: Confirm `pytest` still passes all existing mock endpoint tests in the repo, ensuring we didn't break core logic while extending `service.py`.
2. **UI Tests**: Start the server and ensure `http://127.0.0.1:7084/` correctly serves the HTML bundle.
3. **Workflow E2E**: Drop a dummy PDF via the UI, set a scale, click "Start Optimization Plan", verify dummy metrics generate in the UI, and verify the "Export" button downloads a valid ZIP/XLSX.
4. **Guardrail Tests**: Submit a PDF without calibration/scale. Ensure the UI blocks processing, flashes a modal, and forces manual entry.

## RISKS
- **Local File Paths vs Browser Sandbox**: Browsers mask real paths (returning `C:\fakepath\file.pdf` or similar). `api.py` currently assumes it will receive raw absolute string paths to local files.
  - **Control**: Implement a small multipart form parser in `service.py` to stream uploaded files into a sandbox directory (e.g., `./tmp/job_{uuid}/`), then pass those absolute backend paths downstream to `intake_prepare`.
- **Low-Cost Breach**: Vision ML or OCR scaling out of control when fed highly dense documents.
  - **Control**: Honor the guardrails in `api.py`. Hardcode `vision_enabled = false` and tie it strictly to a UI toggle that warns the user.

## NEXT ACTIONS (Completed)
- [x] **Step 1**: Update `service.py` to route `/` to `index.html` and handle static asset streaming.
- [x] **Step 2**: Build out `index.html`, `styles.css`, and `app.js` using a premium vanilla layout inside a newly created `src/universal_qs_engine/ui` directory.
- [x] **Step 3**: Introduce `multipart/form-data` upload logic so the browser can securely deliver files to the local Python runtime.
- [x] **Step 4**: Provide a wrapper run-script in `0luka/tools/ops` so the system can boot the app via CLI command effortlessly.
- [x] **Step 5**: Test end-to-end integration and handle outputs uniformly.
