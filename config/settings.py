# config/settings.py
# All thresholds sourced from real Indian regulatory standards.
# OISD = Oil Industry Safety Directorate | DGFASLI = Directorate General Factory Advice Service

SENSOR_THRESHOLDS = {
    "H2S": {
        "safe": 5.0, "warning": 10.0, "danger": 20.0, "critical": 50.0,
        "unit": "ppm",
        "source": "OISD-GS-1 Clause 6.3"
    },
    "CO": {
        "safe": 25.0, "warning": 50.0, "danger": 100.0, "critical": 200.0,
        "unit": "ppm",
        "source": "Factory Act 1948 + DGFASLI Annual Report 2023"
    },
    "CH4": {
        "safe": 10.0, "warning": 20.0, "danger": 40.0, "critical": 60.0,
        "unit": "% LEL",
        "source": "OISD-GS-1 Clause 8.1"
    },
    "O2": {
        "safe": 20.9, "warning": 19.5, "danger": 18.0, "critical": 16.0,
        "unit": "%", "invert": True,
        "source": "Factory Act 1948 Section 36"
    },
    "TEMP": {
        "safe": 35.0, "warning": 45.0, "danger": 60.0, "critical": 80.0,
        "unit": "°C",
        "source": "OISD-GS-1 Clause 9.2"
    },
    "PRESSURE": {
        "safe": 2.0, "warning": 3.5, "danger": 5.0, "critical": 7.0,
        "unit": "bar",
        "source": "OISD-GS-1 Clause 7.4"
    }
}

ZONES = {
    "Z-01": "Coke Oven Battery A",
    "Z-02": "Coke Oven Battery B",
    "Z-03": "Coal Handling Area",
    "Z-04": "By-Products Plant",
    "Z-05": "Gas Holder Area",
    "Z-06": "Pump House",
    "Z-07": "Control Room",
    "Z-08": "Confined Space Entry Points",
}

# Compound risk factor weights — must sum to 1.0
COMPOUND_RISK_WEIGHTS = {
    "gas_level":        0.30,
    "active_hot_work":  0.25,
    "sensor_offline":   0.20,
    "shift_changeover": 0.15,
    "no_entry_check":   0.10,
}

# The Vizag incident — Jan 4 2025
VIZAG_INCIDENT = {
    "date": "2025-01-04",
    "plant": "Rashtriya Ispat Nigam Limited (RINL) Vizag Steel",
    "deaths": 8,
    "zone": "Z-08",
    "lead_time_minutes": 47,
    "precursors": [
        "H2S elevated above 8 ppm for 47 min before entry",
        "Sensor G-09 offline since previous shift (blind spot in Z-04)",
        "Hot work permit active in adjacent Z-02 (shared ventilation)",
        "Shift changeover in progress — 23-min supervisor handover gap",
        "Confined space pre-entry atmospheric check not logged"
    ],
    "regulatory_violations": [
        "Factory Act 1948 Section 36 — no valid pre-entry atmospheric test",
        "OISD-GS-1 Clause 6.3 — offline sensor not flagged as safety critical event",
        "DGFASLI Confined Space SOP Clause 4.2 — PTW not integrated with live gas data"
    ]
}