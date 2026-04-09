# ProcureAI — RFQ Intelligence Platform

An end-to-end AI-powered procurement system built with **Python / FastAPI** (backend) and **React / TypeScript** (frontend). Every file is split by concern; nothing is monolithic.

---

## Project Structure

```
procureai/
│
├── backend/                         Python / FastAPI
│   ├── main.py                      App entry point, CORS, router registration
│   ├── requirements.txt
│   ├── .env.example                 Copy to .env and fill in your API key
│   │
│   ├── core/
│   │   ├── config.py                Pydantic-settings — all env vars
│   │   └── database.py              In-memory repository (swap for SQLAlchemy)
│   │
│   ├── models/
│   │   └── schemas.py               All Pydantic v2 request/response models
│   │
│   ├── routers/
│   │   ├── rfq.py                   RFQ CRUD + questionnaire generation
│   │   ├── vendors.py               Vendor document management + seed
│   │   └── analysis.py             4-stage pipeline: extract→technical→commercial→award
│   │
│   └── services/
│       ├── ai_service.py            All Anthropic Claude API calls
│       └── seed_data.py             Demo RFQ + 5 sample vendor documents
│
└── frontend/                        React 18 / TypeScript / Vite
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    │
    └── src/
        ├── main.tsx                 React entry point
        ├── App.tsx                  Root component — layout + routing
        │
        ├── styles/
        │   └── globals.css          Design tokens (CSS vars) + reset
        │
        ├── types/
        │   └── index.ts             All TypeScript interfaces (mirrors backend schemas)
        │
        ├── constants/
        │   └── index.ts             Vendor colours, icons, anomaly colours
        │
        ├── services/
        │   └── api.ts               Typed HTTP client — every API endpoint
        │
        ├── hooks/
        │   ├── useApi.ts            Generic async hook (loading / error / data)
        │   └── useAppState.ts       Central app state — RFQ selection, step nav
        │
        ├── components/
        │   ├── ui/                  Primitive UI components
        │   │   ├── index.ts         Barrel export
        │   │   ├── Button.tsx
        │   │   ├── Card.tsx         Card, CardHeader, CardBody, AiBlock, InsightRow, AnomalyRow
        │   │   ├── DataTable.tsx    Generic typed table
        │   │   ├── ErrorBox.tsx
        │   │   ├── FieldGroup.tsx
        │   │   ├── ScoreBar.tsx
        │   │   ├── Spinner.tsx
        │   │   └── Tag.tsx
        │   │
        │   └── layout/              App chrome components
        │       ├── index.ts         Barrel export
        │       ├── PageShell.tsx    Page wrapper with title + consistent padding
        │       ├── ProgressBar.tsx  6-step workflow progress indicator
        │       ├── Sidebar.tsx      Nav sidebar with RFQ directory + workflow steps
        │       └── Topbar.tsx       Sticky header with breadcrumb + RFQ badge
        │
        └── pages/                   One file per workflow step
            ├── index.ts             Barrel export
            ├── Directory.tsx        RFQ directory — table of all RFQs
            ├── StepA.tsx            RFQ setup + AI questionnaire generation
            ├── StepB.tsx            Vendor document upload / seed
            ├── StepC.tsx            AI extraction + normalisation
            ├── StepD.tsx            AI technical analysis
            ├── StepE.tsx            Commercial comparison dashboard
            └── StepF.tsx            Award recommendation (3 scenarios)
```

---

## Quick Start

### 1 — Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# Run development server
uvicorn main:app --reload --port 8000
```

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | API root |
| `http://localhost:8000/docs` | Swagger UI — interactive API explorer |
| `http://localhost:8000/redoc` | ReDoc documentation |

### 2 — Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open `http://localhost:5173`

---

## API Reference

### RFQ Endpoints (`/rfq`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/rfq/` | List all RFQs |
| `POST` | `/rfq/` | Create a new RFQ |
| `POST` | `/rfq/seed` | Create the demo kids health drink RFQ |
| `GET` | `/rfq/{id}` | Get a single RFQ |
| `PUT` | `/rfq/{id}` | Full update |
| `PATCH` | `/rfq/{id}` | Partial update |
| `DELETE` | `/rfq/{id}` | Delete an RFQ |
| `POST` | `/rfq/{id}/questionnaires` | AI-generate technical + commercial questionnaires |
| `GET` | `/rfq/{id}/questionnaires` | Get cached questionnaires |

### Vendor Endpoints (`/rfq/{id}/vendors`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/vendors/` | List all vendor documents |
| `POST` | `/vendors/` | Add a single vendor document |
| `POST` | `/vendors/seed` | Load all 5 sample vendor documents |
| `GET` | `/vendors/{vid}` | Get a specific vendor |
| `DELETE` | `/vendors/{vid}` | Remove a vendor |
| `DELETE` | `/vendors/` | Clear all vendors |

### Analysis Pipeline (`/rfq/{id}/analysis`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analysis/extract` | Stage 1 — extract + normalise vendor documents |
| `GET` | `/analysis/extract` | Get cached extraction results |
| `DELETE` | `/analysis/extract` | Clear extraction cache |
| `POST` | `/analysis/technical` | Stage 2 — compliance + capability scoring |
| `GET` | `/analysis/technical` | Get cached technical results |
| `DELETE` | `/analysis/technical` | Clear technical cache |
| `POST` | `/analysis/commercial` | Stage 3 — cost comparison + anomaly detection |
| `GET` | `/analysis/commercial` | Get cached commercial results |
| `DELETE` | `/analysis/commercial` | Clear commercial cache |
| `POST` | `/analysis/recommendation` | Stage 4 — multi-scenario award recommendation |
| `GET` | `/analysis/recommendation` | Get cached recommendation |
| `DELETE` | `/analysis/recommendation` | Clear recommendation cache |
| `GET` | `/analysis/summary` | All cached results in one call |
| `DELETE` | `/analysis/all` | Clear all analysis caches |

---

## Workflow

```
Directory → Step A → Step B → Step C → Step D → Step E → Step F
              ↓         ↓         ↓         ↓         ↓         ↓
           RFQ       Vendor    Extract   Technical  Commercial  Award
           Setup     Docs      + Norm    Analysis   Dashboard   Rec.
```

1. **Step A — RFQ Setup**: View the full RFQ (subject, timelines, 8 line items, scope of work). Click "Generate" to have Claude create tailored technical and commercial vendor questionnaires.

2. **Step B — Vendor Docs**: Upload or seed 5 vendor documents (PDF, PPT, Excel, Word). Each contains realistic messy real-world data — hidden pricing, mixed currencies, partial quotes, percentage-only fees.

3. **Step C — Extraction**: Claude reads all documents, normalises currencies to USD, maps pricing to the 8 RFQ line items, and flags anomalies, strengths, and risks per vendor.

4. **Step D — Technical**: Claude scores each vendor on capabilities, compliance evidence (CARU, COPPA, BCAP, ASA, ISO), and scope coverage. Produces a requirements matrix and compliance scorecard.

5. **Step E — Commercial**: Cross-vendor line-item comparison table, anomaly detection (too high, too low, currency conflict, open-ended fees, missing items), cost insights, and value-for-money ranking.

6. **Step F — Award**: Three scored scenarios (best value, lowest cost, split award) with a 100-point weighted model across compliance / scope / cost / timeline / risk. Identifies the recommended winner with rationale and trade-offs.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model to use |
| `ANTHROPIC_MAX_TOKENS` | `2000` | Default max tokens per call |
| `DEBUG` | `true` | Enable FastAPI debug mode |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server port |

---

## Architecture Notes

**Backend**
- `core/database.py` is a simple in-memory dict. Replace the `InMemoryDB` class methods with SQLAlchemy session calls to move to PostgreSQL without touching any router code.
- `services/ai_service.py` is the only file that calls the Anthropic API. Each function accepts plain Python dicts and returns plain dicts — easy to unit-test with mocks.
- All four analysis stages cache their results in the RFQ bucket. `GET` endpoints return cached results; `POST` endpoints re-run AI and overwrite the cache.

**Frontend**
- `hooks/useAppState.ts` is the single source of truth for app-level state. No Redux or Context needed at this scale.
- `services/api.ts` is the only file that calls `fetch()`. All return types are fully typed against `types/index.ts`.
- Every UI primitive is in `components/ui/` and exported from a barrel `index.ts`. Pages import from the barrel, not individual files.
