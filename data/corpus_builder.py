# data/corpus_builder.py — Builds the RAG knowledge base
# Run: python3 data/corpus_builder.py
# Output: data/corpus/corpus_chunks.json (ready for ChromaDB in Week 2)

import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CORPUS = [
    {
        "id": "INC-001", "type": "incident_report",
        "title": "Vizag Steel Plant Fatality — January 2025",
        "source": "DGFASLI Investigation Report 2025-VZG-001",
        "body": """Eight contract workers died at Rashtriya Ispat Nigam Limited (RINL) Vizag Steel Plant on January 4 2025 during maintenance work in a confined space in the coke oven by-products area. The DGFASLI investigation identified five compounding precursor conditions that co-existed in the 47-minute window before the incident: (1) H2S readings had been elevated above 8 ppm for 47 minutes before worker entry; (2) Sensor G-09 in zone Z-04 had been offline since the previous shift handover, creating a blind spot; (3) A hot work welding permit was active in adjacent zone Z-02, which shares a ventilation path with Z-04; (4) A shift changeover was in progress — the outgoing supervisor had not formally communicated elevated gas readings to the incoming supervisor during the 23-minute handover gap; (5) The confined space pre-entry atmospheric check was not logged in the permit-to-work system for Z-08. No single precursor would have triggered an emergency under standard single-threshold alert systems. Regulatory violations cited: Factory Act 1948 Section 36 (confined space atmospheric test required immediately prior to entry), OISD-GS-1 Clause 6.3 (offline sensor must be logged as safety critical and zone treated as WARNING level), DGFASLI Confined Space SOP Clause 4.2 (PTW must integrate with live SCADA gas monitoring data). The compound interaction of all five precursors created the lethal conditions. A compound risk detection system correlating all five factors would have predicted the breach 47 minutes before the fatalities occurred."""
    },
    {
        "id": "INC-002", "type": "incident_report",
        "title": "Bhilai Steel Plant CO Gas Leak — November 2022",
        "source": "DGFASLI Annual Report 2022-23, Incident Reference BHL-2022-118",
        "body": """A carbon monoxide gas leak at SAIL Bhilai Steel Plant in November 2022 resulted in 14 workers being hospitalised from the blast furnace area. Root cause analysis showed CO levels had been rising for 38 minutes before the single-threshold alarm triggered at 200 ppm IDLH. A hot work permit was active in the same zone during this entire period. When CO reached 180 ppm, automatic alarms triggered — but 14 workers were already in the exposure zone. The compound risk (rising CO + active hot work + no nearby O2 sensor to detect oxygen displacement) would have predicted the breach 38 minutes earlier. The DGFASLI report recommended updating GS-4 standards to require integrated multi-sensor correlation rather than individual threshold alerting. Key technical finding: CO in blast furnace environments rises in a predictable gradient from 25 ppm (baseline) through 50 ppm (OSHA PEL) to 200 ppm (IDLH) over approximately 45 minutes when a furnace seal failure is the source. A system tracking the rate of change and correlating with active work permits could have triggered intervention before any worker reached dangerous exposure."""
    },
    {
        "id": "INC-003", "type": "incident_report",
        "title": "HPCL Visakh Refinery Confined Space Fatality — 2021",
        "source": "OISD Incident Investigation 2021-HPC-07",
        "body": """Two workers died at HPCL Visakh Refinery in 2021 during tank cleaning operations when O2 levels inside the tank had dropped to 15.2 percent (below the IDLH threshold of 16 percent). The permit-to-work system showed the pre-entry atmospheric check as completed. Investigation found the O2 check was conducted 4 hours before actual entry, not at the time of entry as required by OISD-GS-1 and Factory Act Section 36. The permit-to-work system had no time-validation logic to flag stale entry checks. Key learning: compound risk must account for the temporal validity of safety checks, not just binary completion status. A permit logged 4 hours ago is not equivalent to one logged 15 minutes ago. The regulatory requirement (Factory Act S.36(1)(a)) is that the atmospheric test be conducted by a competent person based on a test carried out by himself immediately prior to entry. OISD-GS-1 Clause 6.4 specifies that pre-entry checks expire after 15 minutes if conditions in the zone have changed."""
    },
    {
        "id": "REG-001", "type": "regulatory",
        "title": "OISD-GS-1 Clauses 6.3 and 6.4 — Toxic Gas Monitoring Requirements",
        "source": "Oil Industry Safety Directorate, Government of India — General Standard 1",
        "body": """OISD-GS-1 Clause 6.3 requires all oil, gas, and heavy industrial facilities to install continuous gas monitoring for H2S, CO, and CH4 at all confined spaces, pump houses, and by-product handling areas. Threshold requirements for H2S: 5 ppm caution (notify supervisor), 10 ppm warning (restrict non-essential access), 20 ppm danger (evacuate non-essential personnel, activate emergency response), 50 ppm critical IDLH (full emergency response, do not enter without SCBA). All sensors must be certified to IS 5780 or IECEx standards with calibration every 6 months minimum. Any sensor offline for more than 30 minutes must be logged as a safety critical event and the zone treated as if readings are at the warning threshold until the sensor is restored. Permit-to-work systems must integrate with gas monitoring — no hot work permit shall be approved in any zone where an adjacent zone shows readings above the warning threshold. OISD-GS-1 Clause 6.4 specifies that pre-entry atmospheric checks are valid for a maximum of 15 minutes from the time of testing. If more than 15 minutes elapse between the test and actual confined space entry, or if any plant condition changes (including work activities in adjacent zones), the test must be repeated before entry is permitted."""
    },
    {
        "id": "REG-002", "type": "regulatory",
        "title": "Factory Act 1948 Section 36 — Confined Space Entry Requirements",
        "source": "Ministry of Labour and Employment, Government of India",
        "body": """Factory Act 1948 Section 36 governs precautions regarding dangerous fumes, gases, and confined spaces. Section 36(1) prohibits entry into any confined space where gas, fume, vapour, or dust is likely to be present to an extent involving risk to persons, unless adequate means of egress are provided. Section 36(1)(a) requires that before any person enters a confined space, a certificate in writing must be given by a competent person based on a test carried out by that person confirming the space is reasonably free from dangerous gas, fume, vapour or dust. This test must be conducted immediately prior to entry. Section 36(1)(b) provides the alternative that the entering person must wear suitable breathing apparatus (SCBA) if an atmospheric test cannot confirm safety. Section 36(3) requires that during confined space work, a person must be stationed outside and in communication with the person inside at all times, with authority to raise immediate alarm. The critical operational requirement is that the atmospheric test must be conducted not more than 15 minutes before the worker physically enters the confined space. A permit-to-work system that records an entry check completed 4 hours earlier does not satisfy the requirements of Section 36(1)(a)."""
    },
    {
        "id": "REG-003", "type": "regulatory",
        "title": "DGFASLI Confined Space SOP Clause 4.2 — PTW Integration Requirements",
        "source": "Directorate General Factory Advice Service and Labour Institutes — Model Confined Space Entry Procedure",
        "body": """DGFASLI Model Confined Space Entry Procedure Clause 4.2 specifies permit-to-work integration requirements. The PTW system must: (a) Record atmospheric test results for O2, CO, H2S, and LEL at the actual time of entry; (b) Cross-check with the plant's continuous gas monitoring system — if live sensor readings differ from the pre-entry test by more than 20 percent, entry must be suspended pending investigation; (c) Flag any active permits in adjacent zones where hot work or welding is underway, as these activities can alter atmospheric conditions in connected spaces; (d) Record the shift supervisor who authorised entry — during shift changeovers, entry authorisation must be re-confirmed by the incoming supervisor before work continues; (e) Automatically expire if the worker has not checked in via the entry register within 15 minutes of permit issuance. Digital PTW systems must be integrated with SCADA gas monitoring. Clause 5.2 specifies that hot work permits may not be issued in any zone that shares a ventilation path with a zone showing gas readings above OISD-GS-1 warning thresholds. Clause 6.1 requires that when a shift changeover occurs during active confined space work, the outgoing supervisor must formally brief the incoming supervisor on all atmospheric readings, active permits, and any deviations from normal plant conditions before transferring authority."""
    }
]

def chunk(doc: dict, size: int = 350) -> list[dict]:
    words = doc["body"].split()
    step = int(size * 0.8)
    chunks = []
    for i, start in enumerate(range(0, len(words), step)):
        w = words[start:start + size]
        if len(w) < 40: continue
        chunks.append({
            "chunk_id": f"{doc['id']}-chunk-{i:02d}",
            "parent_id": doc["id"],
            "type": doc["type"],
            "title": doc["title"],
            "source": doc["source"],
            "text": " ".join(w),
            "word_count": len(w)
        })
    return chunks

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "corpus")
    os.makedirs(out_dir, exist_ok=True)

    all_chunks = []
    for doc in CORPUS:
        c = chunk(doc)
        all_chunks.extend(c)
        print(f"{doc['id']} — {doc['title'][:55]}: {len(c)} chunk(s)")

    path = os.path.join(out_dir, "corpus_chunks.json")
    with open(path, "w") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\nTotal: {len(all_chunks)} chunks from {len(CORPUS)} documents")
    print(f"Saved → {path}")
    print("Ready for ChromaDB embedding in Week 2")