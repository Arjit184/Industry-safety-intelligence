"""
SafetyIQ — RAG corpus builder

Builds the incident + regulatory knowledge base that the RAG agent queries.

Week 1 task: run this to generate the synthetic corpus.
Week 2 task: replace synthetic docs with real PDFs from DGFASLI, OISD, DGMS.

Real sources to download (all public):
  • DGFASLI annual reports: https://dgfasli.gov.in/en/annual-reports
  • OISD standards (GS-1, STD-105, STD-118): https://oisd.gov.in/standards
  • DGMS circulars: https://dgms.gov.in/circulars
  • CPCB industrial accident reports: https://cpcb.nic.in

Run:  python3 corpus_builder.py --output data/corpus/
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


# ── Synthetic incident corpus ──────────────────────────────────────────────────
# These are fictionalised but technically accurate incident reports.
# Replace with real DGFASLI PDFs in Week 2 using PyMuPDF or pdfplumber.

INCIDENT_TEMPLATES = [
    {
        "id": "INC-001",
        "title": "Coke oven gas leak — confined space fatality, Bhilai Steel Plant, 2019",
        "date": "2019-08-14",
        "plant_type": "integrated_steel",
        "hazard_type": "toxic_gas",
        "fatalities": 2,
        "injuries": 4,
        "root_causes": [
            "Permit-to-work not cross-checked against live gas readings",
            "Gas detector G-4 under calibration — blind spot in battery 7",
            "Shift changeover during confined space entry — communication gap",
        ],
        "precursor_signals": [
            "H2S reading elevated 2.1 ppm above baseline 45 mins prior",
            "Pressure sensor P-3 showed 1.8 kPa above normal at 22:10",
            "No pre-entry atmospheric test recorded in PTW-219",
        ],
        "regulatory_violations": [
            "Factory Act S.36(1) — no atmospheric testing before confined space entry",
            "OISD-GS-1 Clause 6.3 — hot work within 15m of elevated H2S",
            "DGFASLI OM-2018-04 — PTW not suspended on gas reading change",
        ],
        "prevention_actions": [
            "Real-time PTW cross-check with gas sensor readings",
            "Automatic PTW suspension when adjacent sensor exceeds warning threshold",
            "Mandatory re-atmospheric test after any sensor reading change during confined space work",
        ],
        "body": (
            "At 22:47 on 14 August 2019, two contract workers entered an inspection pit "
            "in Battery 7 at Bhilai Steel Plant under PTW-219, authorised for inspection work. "
            "Gas detector G-4 in the adjacent bay was under calibration and offline. "
            "At 22:53, both workers collapsed due to H2S exposure. "
            "Response teams reached the site at 23:04 but both workers were pronounced dead on arrival at hospital. "
            "Investigation found H2S had been trending upward for 47 minutes prior to entry, "
            "visible in the SCADA historian, but no alert was generated because no single sensor "
            "had yet crossed the 10 ppm threshold. The compound condition — elevated gas, "
            "offline sensor, active confined space permit, shift changeover — was never assessed holistically."
        ),
    },
    {
        "id": "INC-002",
        "title": "Coke oven explosion — gas accumulation during maintenance, Durgapur, 2021",
        "date": "2021-03-22",
        "plant_type": "integrated_steel",
        "hazard_type": "explosion",
        "fatalities": 3,
        "injuries": 11,
        "root_causes": [
            "Hot work permit active in Zone C while gas pressure in collector main was elevated",
            "Maintenance team not informed of gas pressure exceedance",
            "Emergency shutdown procedure not initiated when pressure exceeded 8 kPa",
        ],
        "precursor_signals": [
            "Collector main pressure at 7.8 kPa (warning threshold 7.0) for 32 minutes",
            "H2S G-07 showing 8.4 ppm — below 10 ppm threshold but above baseline",
            "PTW-334 (hot work — angle grinding) active in Zone C since 14:30",
        ],
        "regulatory_violations": [
            "OISD-GS-1 Clause 7.1 — hot work not suspended on pressure exceedance",
            "OISD-STD-105 — gas tightness test not performed before maintenance",
            "Factory Act S.36(3) — no gas-free certificate for work area",
        ],
        "prevention_actions": [
            "Automatic hot work permit suspension when adjacent pressure sensor exceeds warning",
            "Real-time gas tightness monitoring during all maintenance activities",
            "Mandatory zone clearance before any hot work in Zone 1 areas",
        ],
        "body": (
            "On 22 March 2021, an explosion occurred in the coke side quench area of Durgapur Steel Plant "
            "at 15:47, killing three workers and injuring eleven. "
            "PTW-334 authorising hot work (angle grinding on a flange) had been active since 14:30. "
            "At 14:58, collector main pressure exceeded the warning threshold of 7.0 kPa, "
            "reaching 7.8 kPa. This reading was visible on SCADA but no alert was sent "
            "to the maintenance team in Zone C. The grinding work continued. "
            "At 15:47, pressure reached 11.2 kPa and gas accumulated around the work area "
            "ignited from the grinding sparks. "
            "Post-incident analysis identified that had the hot work permit been automatically "
            "cross-checked against the live pressure reading, PTW-334 would have been flagged "
            "for suspension at 14:58 — 49 minutes before the explosion."
        ),
    },
    {
        "id": "INC-003",
        "title": "Vizag Steel Plant coke oven explosion — 8 fatalities, January 2025",
        "date": "2025-01-12",
        "plant_type": "integrated_steel",
        "hazard_type": "explosion",
        "fatalities": 8,
        "injuries": 14,
        "root_causes": [
            "No intelligence layer to correlate existing sensor data into compound risk",
            "Gas detector maintenance created coverage blind spot in Battery 3",
            "PTW system not integrated with real-time SCADA readings",
            "Shift changeover incomplete — incoming supervisor not briefed on gas trends",
            "No pre-entry atmospheric test for workers entering coke side",
        ],
        "precursor_signals": [
            "H2S trending upward in Zone C for 73 minutes before explosion",
            "Collector main pressure at 8.6 kPa — above warning, below critical",
            "G-09 offline for calibration — Zone C had reduced sensor coverage",
            "Hot work permit PTW-047 active for angle grinding in Zone C",
            "Shift B/C changeover at 22:00 — incoming supervisor not informed of gas trend",
        ],
        "regulatory_violations": [
            "OISD-GS-1 Clause 6.3 and 7.1 — multiple compound violations",
            "Factory Act S.36(1)(a) — no pre-entry test before Zone C entry",
            "DGFASLI OM-2023-11 — PTW not reviewed after sensor readings changed",
        ],
        "prevention_actions": [
            "Compound risk engine correlating all sensor, permit, shift, and maintenance data",
            "Real-time PTW suspension protocol on compound risk threshold breach",
            "Mandatory shift briefing checklist including live gas trend review",
            "No hot work in Zone 1 when any adjacent sensor in maintenance/offline state",
        ],
        "body": (
            "On 12 January 2025, eight workers were killed and fourteen injured in an explosion "
            "at Coke Oven Battery 3, Visakhapatnam Steel Plant. "
            "An investigation by The Wire found that warning signals from gas pressure sensors existed, "
            "but no intelligence layer connected those readings to operational decisions in time. "
            "Five distinct precursor conditions were identifiable in SCADA data up to 73 minutes before the event: "
            "elevated H2S trending in Zone C, collector main pressure above warning threshold, "
            "gas detector G-09 offline for calibration, hot work permit PTW-047 active in Zone C, "
            "and shift changeover completed without a gas trend briefing. "
            "Each condition was below the threshold for a standalone alert. "
            "Together, they constituted an imminent explosion risk. "
            "The SCADA system logged every reading. The intelligence to act on them was absent."
        ),
    },
]

REGULATORY_DOCS = [
    {
        "id": "REG-001",
        "title": "OISD-GS-1: Safety practices for hydrocarbon industries",
        "source": "Oil Industry Safety Directorate",
        "type": "standard",
        "clauses": {
            "6.3": "Toxic gas monitoring: H2S detectors shall be installed in all areas where H2S concentration may exceed 1 ppm. Hot work shall not be performed when H2S exceeds 5 ppm in the work zone or within 15 metres.",
            "6.4": "Carbon monoxide monitoring: CO detectors required in all confined spaces. Work shall be suspended when CO exceeds 25 ppm.",
            "7.1": "Gas pressure management: Hot work permits shall be automatically suspended when collector main pressure exceeds the warning threshold. All permits must be re-validated after any pressure exceedance event.",
            "5.2": "Explosive atmosphere management: No ignition sources in Zone 1 when CH4 exceeds 10% LEL. Mandatory gas-free certificate before hot work.",
        },
    },
    {
        "id": "REG-002",
        "title": "Factory Act 1948 — Sections 36–41: Dangerous operations",
        "source": "Ministry of Labour and Employment",
        "type": "legislation",
        "clauses": {
            "S.36(1)": "No person shall be required or allowed to enter any confined space in which dangerous fumes are likely to be present unless it has been certified safe by a competent person immediately before entry.",
            "S.36(1)(a)": "Atmospheric testing for oxygen, flammable, and toxic gases must be performed immediately before entry and documented in the permit-to-work system.",
            "S.36(3)": "No naked flame or light likely to ignite fumes shall be used in any confined space.",
            "S.37": "Precautions against explosive or inflammable dust: where explosive dust is liable to be generated, effective measures to prevent accumulation.",
        },
    },
    {
        "id": "REG-003",
        "title": "DGFASLI operational manual OM-2023-11: Permit-to-work for chemical hazards",
        "source": "Directorate General Factory Advice Service & Labour Institutes",
        "type": "operational_manual",
        "clauses": {
            "4.1": "Permit-to-work cross-validation: All PTW systems must be validated against real-time gas monitor readings at the time of issue and at least every 30 minutes during active work.",
            "4.3": "Automatic suspension trigger: PTW shall be suspended immediately when any gas sensor within 20 metres of the work zone exceeds the warning threshold.",
            "5.2": "Shift changeover protocol: Incoming shift supervisor must review all active permits and current gas monitor trends before accepting responsibility.",
            "6.1": "Sensor maintenance: When a gas detector is taken offline for maintenance, no hot work or confined space entry shall be permitted in the coverage area without deployment of a portable backup detector.",
        },
    },
]


def build_corpus(output_dir: str = "data/corpus") -> None:
    """
    Build the RAG corpus and save as JSON files.
    In Week 2, extend this to also ingest real PDFs using:
        pip install pdfplumber
        import pdfplumber
        with pdfplumber.open("OISD-GS-1.pdf") as pdf:
            text = "\n".join(p.extract_text() for p in pdf.pages)
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Save incident corpus
    incidents_path = out / "incidents.json"
    with open(incidents_path, "w") as f:
        json.dump(INCIDENT_TEMPLATES, f, indent=2)
    print(f"Saved {len(INCIDENT_TEMPLATES)} incidents → {incidents_path}")

    # Save regulatory corpus
    regs_path = out / "regulations.json"
    with open(regs_path, "w") as f:
        json.dump(REGULATORY_DOCS, f, indent=2)
    print(f"Saved {len(REGULATORY_DOCS)} regulatory docs → {regs_path}")

    # Build flat text chunks for vector embedding (Week 2)
    chunks = []
    for inc in INCIDENT_TEMPLATES:
        chunks.append({
            "id": f"{inc['id']}_body",
            "type": "incident_report",
            "text": inc["body"],
            "metadata": {
                "incident_id": inc["id"],
                "date": inc["date"],
                "fatalities": inc["fatalities"],
                "hazard_type": inc["hazard_type"],
                "precursor_signals": inc["precursor_signals"],
            },
        })
        for i, cause in enumerate(inc["root_causes"]):
            chunks.append({
                "id": f"{inc['id']}_cause_{i}",
                "type": "root_cause",
                "text": f"Root cause of {inc['title']}: {cause}",
                "metadata": {"incident_id": inc["id"]},
            })
        for i, action in enumerate(inc["prevention_actions"]):
         chunks.append({
        "id": f"{inc['id']}_prevention_{i}",
        "type": "prevention_action",
        "text": action,
        "metadata": {"incident_id": inc["id"]},
    })

    for reg in REGULATORY_DOCS:
        for clause_id, text in reg["clauses"].items():
            chunks.append({
                "id": f"{reg['id']}_{clause_id}",
                "type": "regulation",
                "text": f"{reg['title']} — {clause_id}: {text}",
                "metadata": {
                    "reg_id": reg["id"],
                    "source": reg["source"],
                    "clause": clause_id,
                },
            })

    chunks_path = out / "chunks.json"
    with open(chunks_path, "w") as f:
        json.dump(chunks, f, indent=2)
    print(f"Saved {len(chunks)} text chunks → {chunks_path}")
    


if __name__ == "__main__":
    build_corpus()