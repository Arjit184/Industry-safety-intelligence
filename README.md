# SafetyIQ — Industrial Safety Intelligence
**ET AI Hackathon 2026 · Problem 1: Zero-Harm Operations**

> **Live demo:** https://codeorbits-navy.vercel.app/ 
> **Backend API:** https://industry-safety-intelligence.onrender.com
---

## The problem

On 12 January 2025, eight workers were killed at Visakhapatnam Steel Plant when gases exploded in Coke Oven Battery 3. Warning signals existed in SCADA data for **73 minutes** before the explosion. Five distinct risk factors were all active simultaneously — elevated H2S, offline sensor, active hot work permit, incomplete shift handover, no confined space pre-entry check. Not one was above a single-sensor alert threshold. Together, they were fatal.

No system connected the dots.

**SafetyIQ is that system.**

---

## What it does

SafetyIQ detects **compound risk** — dangerous combinations of conditions that no single sensor sees alone.

| | Single-sensor baseline | SafetyIQ |
|--|----------------------|----------|
| Vizag pattern detected | Minute 156 | **Minute 11** |
| Lead time | 0 minutes | **145 minutes** |
| False negative rate | 100% | **0%** |
| Regulations auto-cited | 0 | **8** |

---

## System architecture

```
┌─────────────────────────────────────────────────────┐
│                   Data Layer                        │
│  IoT/SCADA → Permit logs → Shift records → Incidents│
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│               AI Agent Layer                        │
│                                                     │
│  Risk Engine          RAG Agent      Orchestrator   │
│  (compound scoring) → (ChromaDB)  → (Claude API)   │
│                                                     │
│  5 factors × weights × compound multipliers         │
│  → RiskAssessment (score 0–100, level, prediction)  │
└──────────────────────┬──────────────────────────────┘
                       │ WebSocket (2s interval)
┌──────────────────────▼──────────────────────────────┐
│              React Dashboard                        │
│  Risk ring · Plant heatmap · Sensor grid            │
│  Compound triggers · RAG context · Claude alert     │
│  Countdown timer · EVACUATE button                  │
└─────────────────────────────────────────────────────┘
```

---

## Folder structure

```
safetyiq/
├── config/
│   └── settings.py                ← sensor thresholds, risk weights, scenarios
│
├── data/
│   ├── simulator.py               ← IoT/SCADA simulator — 4 demo scenarios
│   ├── adapter.py                 ← simulator JSON → typed PlantReading
│   ├── corpus_builder.py          ← builds RAG incident + regulation corpus
│   ├── embed_corpus.py            ← embeds corpus into ChromaDB vector store
│   ├── historical_generator.py    ← 6-month synthetic dataset + stats
│   └── corpus/
│       ├── __init__.py
│       ├── incidents.py           ← 7 real industrial incidents
│       ├── incidents.json         ← serialised incident corpus
│       ├── regulations.json       ← OISD-GS-1, Factory Act, DGFASLI clauses
│       └── chunks.json            ← 46 text chunks for vector embedding
│
├── agents/
│   ├── interfaces.py              ← shared data contract (PlantReading, RiskAssessment)
│   ├── adapter.py                 ← import shim (from data.adapter)
│   ├── risk_engine.py             ← compound risk scoring engine
│   ├── rag_agent.py               ← ChromaDB semantic search
│   ├── alert_generator.py         ← Claude API natural language alerts
│   └── tests/
│       ├── test_risk_engine.py    ← 9 risk engine tests
│       └── test_rag_and_alerts.py ← 17 RAG + alert tests
│
├── tests/
│   └── test_backend.py            ← 47 API + simulator + adapter tests
│
├── frontend/                      ← React dashboard (Vite)
│   └── src/
│       ├── App.jsx
│       ├── hooks/useRiskStream.js  ← WebSocket with auto-reconnect + cache
│       └── components/
│           ├── RiskScore.jsx       ← animated ring + countdown timer
│           ├── PlantMap.jsx        ← live zone heatmap
│           ├── ConnectionStatus.jsx← loading screen + cached banner
│           └── index.jsx           ← SensorGrid, AlertFeed, PermitPanel, etc.
│
├── main.py                        ← FastAPI server + WebSocket endpoints
├── render.yaml                    ← Render deployment config
├── requirements.txt
└── .env.example
```

---

## Quick start

```bash
# 1. Clone and set up
git clone <repo>
cd safetyiq
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Environment
cp .env.example .env
# Add: ANTHROPIC_API_KEY=your_key_here

# 3. Build the RAG corpus
python3 data/corpus_builder.py
python3 data/embed_corpus.py    # first run ~2 min (downloads embedding model)

# 4. Start backend
uvicorn main:app --reload --port 8000

# 5. Start frontend (new terminal)
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check — shows `risk_engine_loaded` status |
| GET | `/scenarios` | List all 4 scenarios with metadata |
| GET | `/assessment/{scenario}` | Full RiskAssessment snapshot |
| GET | `/zones` | Plant zone definitions for heatmap |
| GET | `/thresholds` | Sensor thresholds with regulatory sources |
| GET | `/vizag` | Vizag incident data — 5 precursors, 8 violations |
| GET | `/api/stats` | Detection comparison stats for slides |
| WS | `/ws/stream/{scenario}` | Live stream — one update every 2 seconds |
| WS | `/ws/escalation` | Judge demo mode — auto-cycles all 4 scenarios |

**WebSocket payload includes:**
`risk_score`, `risk_level`, `compound_triggers`, `recommended_actions`,
`rag_context`, `nl_alert`, `sensors`, `active_permits`, `shift`,
`prediction`, `regulatory_violations`, `incident_report_draft`

---

## Run the tests

```bash
pytest tests/ -v          # 47 backend tests
pytest agents/tests/ -v   # 26 agent tests (9 + 17)
# Total: 73 tests
```

---

## The 4 demo scenarios

| Scenario | Risk level | What it shows |
|----------|-----------|---------------|
| `normal_ops` | LOW | Baseline — all green |
| `gas_rising` | WARNING | H2S trending, no single-sensor alert yet |
| `hot_work_conflict` | HIGH/CRITICAL | Compound trigger: gas + hot work permit |
| `vizag_pattern` | CRITICAL | All 5 Vizag precursors active simultaneously |

Switch scenarios live from the dashboard. The `hot_work_gas` alias also works (maps to `hot_work_conflict`).

---

## Key numbers

| Number | What it means |
|--------|--------------|
| **8** | Workers killed at Vizag, 12 January 2025 |
| **73** | Minutes precursor signals were in SCADA before explosion |
| **5** | Compound risk factors active simultaneously |
| **11** | Minute at which SafetyIQ flags CRITICAL |
| **156** | Minute at which single-sensor baseline would have fired |
| **145** | Our lead time advantage in minutes |
| **0%** | False negative rate on compound conditions |
| **73** | Total tests passing |

---

## Regulatory coverage

SafetyIQ auto-cites 8 specific regulatory clauses in real time:

- **OISD-GS-1 Clause 6.3** — H2S monitoring and hot work exclusion zones
- **OISD-GS-1 Clause 6.4** — CO monitoring in confined spaces
- **OISD-GS-1 Clause 6.5** — CH4 explosive atmosphere management
- **OISD-GS-1 Clause 7.1** — Hot work permit suspension on gas exceedance
- **Factory Act S.36(1)** — Confined space atmospheric certification
- **Factory Act S.36(1)(a)** — Pre-entry gas test documentation
- **Factory Act S.36(3)** — No ignition sources in gas-affected areas
- **DGFASLI OM-2023-11 Cl.4.3** — PTW cross-check against live readings
- **DGFASLI OM-2023-11 Cl.5.2** — Shift handover gas trend transfer
- **DGFASLI OM-2023-11 Cl.6.1** — Backup detector when fixed sensor offline

---

## Team

| Member | Role |
|--------|------|
| Member 1 | AI / Agent engineer — risk engine, RAG, Claude integration |
| Member 2 | Data + backend — simulator, FastAPI server, deployment |
| Member 3 | Frontend + UI — React dashboard, WebSocket, Vercel |
| Member 4 | Research + presentation — regulatory analysis, demo script, deck |

---

*ET AI Hackathon 2026 · Problem 1: Industrial Safety Intelligence — Zero Harm*