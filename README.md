# BI Dashboard Validator

Production-oriented AI-assisted validation service for BI dashboards such as Tableau, Power BI, Looker, and custom analytics apps. The system opens dashboards in a real browser, discovers clickable visuals, drills through navigation paths, validates data consistency, enforces UI rules from YAML, and generates HTML/CSV/JSON reports with screenshots.

The app also ships with a browser UI at `/` so you can paste a dashboard URL, login credentials, and login selectors directly into the product without starting from Swagger or a YAML file.

## Single Executable Packaging

You cannot produce one identical executable that runs on Windows, macOS, and Linux. Native executables are OS-specific, so the correct production approach is:

- build one file on Windows for Windows
- build one file on macOS for macOS
- build one file on Linux for Linux

This repository now includes a standalone launcher that starts the API and browser UI from a single executable, using:

- local SQLite by default instead of PostgreSQL
- inline background execution by default instead of Redis workers
- bundled Playwright Chromium binaries
- the same browser UI at `/`

### Build the executable

Install dependencies first:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Then build the one-file executable:

```bash
python scripts/build_executable.py
```

This command:

- installs a local Playwright Chromium bundle into `.playwright-browsers/`
- runs PyInstaller with `packaging/bi_validator.spec`
- produces a one-file executable under `dist/`

### Run the executable

After the build completes, start the packaged app:

```bash
./dist/bi-dashboard-validator
```

The executable starts a local server, opens the browser UI automatically, and stores data here by default:

- macOS: `~/Library/Application Support/bi-dashboard-validator`
- Linux: `~/.local/share/bi-dashboard-validator`
- Windows: `%APPDATA%\\bi-dashboard-validator`

Useful flags:

```bash
./dist/bi-dashboard-validator --port 8010
./dist/bi-dashboard-validator --no-browser
./dist/bi-dashboard-validator --show-automation-browser
```

### Standalone behavior

The packaged executable is optimized for local desktop usage:

- validation history is stored in a local SQLite database
- queued validation runs execute in-process without Redis
- scheduled jobs still require Redis-backed service mode
- if you want PostgreSQL or Redis anyway, set `DATABASE_URL` and `REDIS_URL` before launch

## Architecture

- `FastAPI` exposes validation run APIs and report retrieval.
- `Playwright` drives live browser sessions and recursively traverses drilldowns.
- `PostgreSQL` stores run metadata, navigation logs, findings, and artifacts.
- `Redis` + `RQ` execute validation jobs in parallel workers.
- `RQ Scheduler` supports recurring validation jobs on cron schedules.
- `YAML` controls UI, data, and execution rules.
- Optional `OpenAI` workflow planning prioritizes drill paths from natural-language prompts.

## Project Layout

```text
src/bi_validator/
  api/                    FastAPI routes
  core/                   settings, config loading, logging, utilities
  db/                     SQLAlchemy session/base
  models/                 ORM models for runs, findings, logs, artifacts
  schemas/                API and YAML config schemas
  services/
    adapters/             platform adapters (generic, Tableau, Power BI, Looker)
    automation/           Playwright crawler and traversal types
    ai/                   prompt-to-workflow planner
    validation/           UI, chart, and data validators
    reporting/            HTML/CSV/JSON report generation
    queue/                Redis/RQ enqueue + worker entrypoint
config/
  dashboards/             example dashboard definitions
  rules/                  validation rules
scripts/                  local helper entrypoints
tests/                    validator and reporting tests
```

## Core Capabilities

1. Dashboard traversal
   - Discovers KPIs, charts, tables, and clickable visuals using DOM heuristics.
   - Clicks into drilldowns until the configured depth limit or navigation terminates.
   - Stores each navigation step with chart type, screenshot, state hash, and path.
2. Data consistency validation
   - Extracts visible numeric measures and grouped values.
   - Compares parent totals against child aggregates with configurable tolerance.
   - Flags missing totals and drilldown mismatches.
3. UI consistency validation
   - Checks typography, spacing, alignment, currency/date formats, legends, headers, and axis labels.
   - Applies chart-specific rules for KPI cards, tables, bar charts, line charts, pie charts, and multi-series visuals.
4. Reporting and observability
   - Writes `report.json`, `report.csv`, and `report.html`.
   - Captures screenshots for dashboard root and each inspected visual.
   - Persists structured execution logs and artifacts.

## Quick Start

### 1. Install locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
cp .env.example .env
```

### 2. Start infrastructure

```bash
docker compose up -d postgres redis
alembic upgrade head
```

### 3. Run the API and worker

```bash
make run-api
make run-worker
```

### 4. Submit a validation run

```bash
curl -X POST http://localhost:8000/api/v1/validation-runs \
  -H "Content-Type: application/json" \
  -d '{
    "dashboard_name": "Sales Overview",
    "dashboard_url": "https://example-bi.local/sales-overview",
    "platform": "generic",
    "prompt": "Validate the Sales dashboard and verify that revenue drilldowns match totals.",
    "rules_path": "config/rules/default_rules.yaml",
    "dashboard_config_path": "config/dashboards/sample_sales.yaml"
  }'
```

### 4a. Use the browser UI

Open [http://localhost:8000/](http://localhost:8000/) and fill in:

- dashboard name and dashboard URL
- platform
- prompt
- optional username/password
- username selector, password selector, submit selector, and post-login wait selector

The UI posts to the direct launch endpoint and then links to the generated HTML/CSV/JSON reports.

### 5. Run inline for local debugging

```bash
python scripts/run_example_validation.py \
  --dashboard-url https://example-bi.local/sales-overview \
  --dashboard-config-path config/dashboards/sample_sales.yaml \
  --rules-path config/rules/default_rules.yaml
```

## API Endpoints

- `GET /api/v1/health`
- `POST /api/v1/validation-runs`
- `POST /api/v1/validation-schedules`
- `POST /api/v1/validation-runs/direct`
- `POST /api/v1/validation-runs/launch`
- `GET /api/v1/validation-runs`
- `GET /api/v1/validation-runs/{run_id}`
- `GET /api/v1/validation-runs/{run_id}/reports`
- `GET /api/v1/validation-runs/{run_id}/reports/{html|json|csv}`

## Configuration

Validation rules are defined in YAML. Example:

```yaml
ui_rules:
  typography:
    font_family: "Inter"
    title_font_size_px: 16
data_rules:
  allow_variance_percent: 0.1
chart_rules:
  table:
    require_headers: true
```

Dashboard definitions support login automation and navigation hints:

```yaml
login_steps:
  - action: "fill"
    selector: "input[name='username']"
    env: "DASHBOARD_USERNAME"
```

Recurring jobs can be scheduled with a cron expression:

```bash
curl -X POST http://localhost:8000/api/v1/validation-schedules \
  -H "Content-Type: application/json" \
  -d '{
    "dashboard_name": "Sales Overview",
    "dashboard_url": "https://example-bi.local/sales-overview",
    "platform": "generic",
    "prompt": "Validate daily sales drilldowns.",
    "rules_path": "config/rules/default_rules.yaml",
    "dashboard_config_path": "config/dashboards/sample_sales.yaml",
    "cron": "0 6 * * 1-5"
  }'
```

## Production Notes

- Use environment variables or a secret manager for credentials referenced by YAML `env` keys.
- Run `api` and `worker` as separate processes or containers.
- Use PostgreSQL for persisted run history and Redis for horizontal worker scaling.
- Tune platform selectors per deployment by extending the adapter classes.
- If LLM support is enabled, set `LLM_PROVIDER=openai` plus `OPENAI_API_KEY`.
