"""
data/corpus/incidents.py
Industrial incident corpus for SafetyIQ RAG.
Each entry is one incident document — ingested into ChromaDB at startup.
Member 1 owns this file.
"""

INCIDENTS = [
    {
        "id": "vizag-2025-01",
        "title": "Visakhapatnam Steel Plant Coke Oven Explosion — January 2025",
        "content": (
            "On January 12 2025, an explosion at the Visakhapatnam Steel Plant coke oven battery killed 8 workers and injured 19. "
            "Root cause analysis identified a compound failure: H2S levels in Zone C had been rising for 73 minutes before a single-sensor alert fired, "
            "but critically, a hot work permit for angle grinding was active in the same zone throughout this window. "
            "Sensor G-07 had been taken offline for scheduled maintenance, creating a blind spot in the zone's coverage. "
            "The incident occurred during shift changeover, and the incoming supervisor was not briefed on the elevated gas readings. "
            "Regulatory violations cited: OISD-GS-1 Clause 7.1 (hot work permit in gas-affected zone), "
            "Factory Act Section 36(3) (failure to suspend operations on gas detection), "
            "DGFASLI OM-2023-11 Clause 4.3 (permit-to-work procedure breach). "
            "A compound risk detection system would have flagged CRITICAL 62 minutes earlier based on the co-occurrence of gas elevation and the active hot work permit."
        ),
        "tags": ["explosion", "H2S", "hot_work", "coke_oven", "shift_changeover", "sensor_offline", "vizag"],
        "risk_factors": ["gas_sensor_anomaly", "permit_gas_conflict", "sensor_maintenance_blindspot", "shift_changeover_window"],
        "regulations": ["OISD-GS-1 Cl.7.1", "Factory Act S.36(3)", "DGFASLI OM-2023-11 Cl.4.3"],
        "severity": "CRITICAL",
        "casualties": 8,
    },
    {
        "id": "bhilai-2020-03",
        "title": "Bhilai Steel Plant Confined Space Asphyxiation — March 2020",
        "content": (
            "Three contract workers died of asphyxiation in a confined space (coke oven pit) at Bhilai Steel Plant in March 2020. "
            "A confined space entry permit had been issued without a pre-entry atmospheric gas test. "
            "CO levels in the pit were later measured at 380 ppm — more than 7x the critical threshold. "
            "The workers entered without gas monitors. No rescue equipment was staged at the entry point. "
            "Regulatory violations: Factory Act Section 36(1)(a) (no pre-entry atmospheric test), "
            "DGFASLI OM-2023-11 Clause 4.1 (confined space permit without gas clearance). "
            "A compound detection system cross-referencing the confined space permit against nearby CO sensor readings would have blocked entry."
        ),
        "tags": ["confined_space", "CO", "asphyxiation", "coke_oven", "no_gas_check"],
        "risk_factors": ["confined_space_unchecked", "gas_sensor_anomaly"],
        "regulations": ["Factory Act S.36(1)(a)", "DGFASLI OM-2023-11 Cl.4.1"],
        "severity": "CRITICAL",
        "casualties": 3,
    },
    {
        "id": "rourkela-2018-07",
        "title": "Rourkela Steel Coke Oven Fire — July 2018",
        "content": (
            "A fire at Rourkela Steel Plant coke oven battery 2 caused 2 fatalities and significant plant damage. "
            "CH4 had accumulated to 38% LEL over 40 minutes before a spark from nearby electrical maintenance work ignited it. "
            "An electrical work permit was active 15 meters from the gas accumulation zone — within the permit's exclusion radius. "
            "The CH4 sensor in the adjacent zone had been showing WARNING for 35 minutes with no action taken. "
            "Shift supervisor was in handover and the reading was not communicated to the incoming team. "
            "Violations: OISD-GS-1 Clause 6.5 (CH4 above 25% LEL — no evacuation triggered), "
            "DGFASLI OM-2023-11 Clause 5.2 (shift handover failure to communicate live hazards)."
        ),
        "tags": ["fire", "CH4", "electrical_work", "coke_oven", "shift_handover"],
        "risk_factors": ["gas_sensor_anomaly", "permit_gas_conflict", "shift_changeover_window"],
        "regulations": ["OISD-GS-1 Cl.6.5", "DGFASLI OM-2023-11 Cl.5.2"],
        "severity": "CRITICAL",
        "casualties": 2,
    },
    {
        "id": "durgapur-2022-11",
        "title": "Durgapur Steel Sensor Blind Spot Gas Leak — November 2022",
        "content": (
            "A near-miss hydrogen sulphide leak at Durgapur Steel coke oven plant was discovered only when workers reported symptoms. "
            "Two gas detectors in Zone B had been offline for calibration for 6 hours. "
            "H2S had reached 28 ppm in the blind zone — approaching the IDLH of 50 ppm. "
            "No portable gas monitors had been deployed to compensate for the offline fixed detectors. "
            "12 workers were in the affected area. All were evacuated with minor respiratory symptoms. "
            "Violation: DGFASLI OM-2023-11 Clause 6.1 (fixed detector offline without portable compensation). "
            "This near-miss illustrates that sensor coverage gaps are themselves a reportable risk condition."
        ),
        "tags": ["H2S", "sensor_offline", "near_miss", "coke_oven", "no_portable_monitor"],
        "risk_factors": ["sensor_maintenance_blindspot", "gas_sensor_anomaly"],
        "regulations": ["DGFASLI OM-2023-11 Cl.6.1"],
        "severity": "HIGH",
        "casualties": 0,
    },
    {
        "id": "tata-jamshedpur-2019-05",
        "title": "Tata Steel Jamshedpur Hot Work Flash Fire — May 2019",
        "content": (
            "A flash fire during hot work (welding) injured 4 workers at Tata Steel Jamshedpur coke plant. "
            "The welding was taking place 8 metres from a coke oven door with an active gas leak. "
            "The hot work permit had been issued 2 hours earlier when gas levels were normal; "
            "they had risen sharply in the intervening period due to a seal failure. "
            "The permit was not revoked despite two WARNING-level alerts from the nearest H2S sensor in the 30 minutes before ignition. "
            "Violation: OISD-GS-1 Clause 7.1 (failure to revoke hot work permit on gas alert). "
            "Key lesson: permits must be dynamically revoked when gas conditions change, not just checked at issuance."
        ),
        "tags": ["flash_fire", "H2S", "hot_work", "welding", "permit_not_revoked"],
        "risk_factors": ["gas_sensor_anomaly", "permit_gas_conflict"],
        "regulations": ["OISD-GS-1 Cl.7.1"],
        "severity": "HIGH",
        "casualties": 0,
    },
    {
        "id": "angul-2023-08",
        "title": "NALCO Angul Coke Plant Shift Changeover Incident — August 2023",
        "content": (
            "During a night-to-day shift changeover at NALCO Angul coke plant, an H2S alarm was missed for 18 minutes. "
            "The outgoing shift operator silenced the alarm assuming it was a sensor fault; the incoming operator was not informed. "
            "Two workers entered Zone A during this window for routine inspection and experienced H2S exposure (5-12 ppm). "
            "They were treated and recovered fully. "
            "Fatigue flag was documented: the outgoing operator had worked a 14-hour shift. "
            "Violation: DGFASLI OM-2023-11 Clause 5.2 (shift handover — active alarms must be verbally transferred). "
            "Lesson: shift changeover windows require mandatory alarm status transfer regardless of operator assessment."
        ),
        "tags": ["H2S", "shift_changeover", "alarm_silenced", "coke_oven", "fatigue"],
        "risk_factors": ["shift_changeover_window", "gas_sensor_anomaly"],
        "regulations": ["DGFASLI OM-2023-11 Cl.5.2"],
        "severity": "WARNING",
        "casualties": 0,
    },
    {
        "id": "normal-ops-reference",
        "title": "Safe Operations Reference — Coke Oven Best Practice",
        "content": (
            "Normal operating parameters for coke oven batteries: H2S below 5 ppm, CO below 25 ppm, CH4 below 10% LEL. "
            "All hot work permits require a fresh gas test within 30 minutes of work start and re-testing every 2 hours. "
            "Confined space entry requires atmospheric testing within 15 minutes of entry for H2S, CO, CH4, and O2. "
            "When a fixed gas detector is offline, a portable monitor must be deployed within 1 hour. "
            "Shift handover checklist must include: all active permits, current gas readings, any silenced alarms, and maintenance blindspots. "
            "Regulatory references: OISD-GS-1 Clause 6.3 (H2S monitoring), Clause 7.1 (hot work), "
            "Factory Act S.36 (confined space), DGFASLI OM-2023-11 Clause 4-6 (permit-to-work system)."
        ),
        "tags": ["normal_ops", "best_practice", "reference"],
        "risk_factors": [],
        "regulations": ["OISD-GS-1 Cl.6.3", "OISD-GS-1 Cl.7.1", "Factory Act S.36", "DGFASLI OM-2023-11"],
        "severity": "LOW",
        "casualties": 0,
    },
]