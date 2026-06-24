# SafetyIQ — Industrial Safety Intelligence Platform
**ET AI Hackathon 2026 · Problem 1: Zero-Harm Operations**

---

## What this is

SafetyIQ detects compound industrial risk — dangerous *combinations* of conditions that no single sensor sees alone.

**The Vizag incident (Jan 2025):** 8 workers killed. Warning signals in SCADA for 73 minutes. No system connected them.  
**SafetyIQ:** Flags CRITICAL at minute 11. Single-sensor baseline: minute 156. **145-minute lead time.**

---

## Team

| Member | Role | Owns |
|--------|------|------|
| M1 | AI / Agent engineer | `agents/risk_engine.py`, `agents/rag_agent.py` |
| M2 | Data + backend | `data/`, `main.py`, `tests/` |
| M3 | Frontend + UI | `frontend/` |
| M4 | Research + presentation | Slide deck, demo script |

---

## Folder structure

```
safetyiq/
├── config/
│   └── settings.py           ← all thresholds, weights, scenarios (M2)
├── data/
│   ├── simulator.py          ← IoT/SCADA simulator — 4 scenarios (M2)
│   ├── adapter.py            ← simulator JSON → PlantReading types (M2)
│   ├── corpus_builder.py     ← builds RAG knowledge base (M2)
│   ├── embed_corpus.py       ← embeds corpus into ChromaDB (M2)
│   ├── historical_generator.py ← 6-month synthetic dataset (M2)
│   └── corpus/
│       ├── incidents.json    ← 3 incident reports
│       ├── regulations.json  ← OISD-GS-1, Factory Act, DGFASLI
│       └── chunks.json       ← 47 text chunks for RAG
├── agents/
│   ├── interfaces.py         ← shared data types (M1 logic, M2 adapter)
│   ├── risk_engine.py        ← compound risk scoring (M1 — Week 1)
│   └── rag_agent.py          ← incident pattern matching (M1 — Week 2)
├── tests/
│   └── test_backend.py       ← 30 tests for M2's code
├── frontend/                 ← React dashboard (M3)
├── main.py                   ← FastAPI server + WebSocket (M2)
├── requirements.txt
└── .env.example
```

---

## Quick start

```bash
# 1. Clone and set up
git clone <repo>
cd safetyiq
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Build the RAG corpus
python3 data/corpus_builder.py

# 4. Embed the corpus into ChromaDB (takes ~2 min first time — downloads model)
python3 data/embed_corpus.py

# 5. Run the backend
uvicorn main:app --reload --port 8000

# 6. Run the frontend (separate terminal)
cd frontend && npm install && npm run dev
# → http://localhost:3000
```

---

## Run the tests

```bash
# From project root
pytest tests/ -v

# Expected: all 30 tests pass
```

---

## Test the simulator directly

```bash
# Stream the Vizag scenario live
python3 data/simulator.py --scenario vizag_pattern --stream

# Single snapshot (prints JSON)
python3 data/simulator.py --scenario normal_ops

# Generate 6-month historical dataset
python3 data/historical_generator.py --days 180
# Prints detection comparison: compound vs single-sensor false negative rate
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/api/scenarios` | List all 4 scenarios |
| GET | `/api/snapshot/{scenario}` | Single reading |
| GET | `/api/zones` | Plant zone definitions |
| WS | `/ws/stream/{scenario}` | Live stream (2s interval) |

**WebSocket from JavaScript:**
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/stream/vizag_pattern")
ws.onmessage = (e) => setAssessment(JSON.parse(e.data))
```

---

## Key numbers

| Number | Meaning |
|--------|---------|
| 8 | Workers killed at Vizag, January 2025 |
| 73 | Minutes precursor signals were in SCADA before explosion |
| 5 | Compound risk factors active simultaneously |
| 11 | Minutes when SafetyIQ flags CRITICAL |
| 156 | Minutes when single-sensor baseline fires |
| **145** | **Our lead time advantage** |