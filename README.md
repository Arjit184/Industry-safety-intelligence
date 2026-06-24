# SafetyIQ — Week 1 deliverables

## What's built

```
safetyiq/
├── config/settings.py       ← All sensor thresholds, zones, scenario params
├── data/
│   ├── simulator.py         ← IoT/SCADA data simulator (4 scenarios)
│   └── corpus_builder.py    ← RAG corpus: incidents + regulations
├── main.py                  ← FastAPI server + WebSocket streaming
└── requirements.txt
```

## Run the simulator

```bash
# Stream a scenario to stdout
python3 data/simulator.py --scenario vizag_pattern --stream

# Generate 6 months of historical data
python3 data/simulator.py --historical --output data/ --days 180

# Available scenarios:
#   normal_ops         → baseline, everything fine
#   gas_rising         → H2S trending up
#   hot_work_conflict  → hot work permit + gas = compound risk
#   vizag_pattern      → all 5 Vizag precursors active
```

## Build the RAG corpus

```bash
python3 data/corpus_builder.py
# → data/corpus/incidents.json   (3 fictionalised incident reports)
# → data/corpus/regulations.json (OISD-GS-1, Factory Act, DGFASLI OM)
# → data/corpus/chunks.json      (36 text chunks ready for embedding)
```

## Run the API server

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Endpoints:
#   GET  /api/scenarios              → list scenarios
#   GET  /api/reading/vizag_pattern  → snapshot
#   WS   /ws/stream/vizag_pattern    → live stream
```

## Week 2 next steps

1. Build the compound risk agent (agents/risk_agent.py)
2. Embed the corpus: `pip install chromadb sentence-transformers`
3. Connect the RAG agent to the vector store
4. Add permit-condition correlator logic