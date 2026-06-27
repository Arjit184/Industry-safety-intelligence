"""
SafetyIQ — central config
Merged to work with both Member 2's backend and Member 1's risk engine.
"""

from dataclasses import dataclass
from typing import Dict, List

# ── Risk weights ──────────────────────────────────────────────────────────────
RISK_WEIGHTS = {
    "gas_sensor_anomaly":           0.30,
    "permit_gas_conflict":          0.35,
    "confined_space_unchecked":     0.20,
    "shift_changeover_window":      0.08,
    "sensor_maintenance_blindspot": 0.07,
}

COMPOUND_MULTIPLIERS = {
    ("gas_sensor_anomaly", "permit_gas_conflict"):          1.8,
    ("confined_space_unchecked", "gas_sensor_anomaly"):     1.5,
    ("sensor_maintenance_blindspot", "gas_sensor_anomaly"): 1.3,
}

# ── Sensor thresholds — plain dict format (Member 1's risk_engine expects this) ──
SENSOR_THRESHOLDS = {
    "H2S": {
        "warning": 5.0, "critical": 10.0, "idlh": 50.0,
        "unit": "ppm", "regulatory_ref": "OISD-GS-1 Clause 6.3",
    },
    "CO": {
        "warning": 25.0, "critical": 50.0, "idlh": 1200.0,
        "unit": "ppm", "regulatory_ref": "OISD-GS-1 Clause 6.4",
    },
    "CH4": {
        "warning": 10.0, "critical": 25.0, "idlh": 60.0,
        "unit": "%LEL", "regulatory_ref": "OISD-GS-1 Clause 6.5",
    },
    "TEMP": {
        "warning": 85.0, "critical": 120.0, "idlh": None,
        "unit": "°C", "regulatory_ref": "Factory Act S.21",
    },
    "PRESSURE": {
        "warning": 105.0, "critical": 120.0, "idlh": None,
        "unit": "kPa", "regulatory_ref": "OISD-GS-1 Clause 8.1",
    },
    "O2": {
        "warning": 19.5, "critical": 16.0, "idlh": None,
        "unit": "%", "regulatory_ref": "Factory Act S.36(1)(a)",
    },
}

# ── Scenario configs — Member 1's simulator format ────────────────────────────
SCENARIO_CONFIGS = {
    "normal_ops": {
        "description": "Routine operations, all sensors nominal",
        "gas_base": {"H2S": 1.0, "CO": 10.0, "CH4": 3.0},
        "gas_rate": {"H2S": 0.05, "CO": 0.2, "CH4": 0.1},
        "permits": [],
        "offline_sensors": [],
        "shift_changeover": False,
    },
    "gas_rising": {
        "description": "Gas slowly increasing — no permit conflict yet",
        "gas_base": {"H2S": 3.0, "CO": 18.0, "CH4": 6.0},
        "gas_rate": {"H2S": 0.15, "CO": 0.5, "CH4": 0.3},
        "permits": [],
        "offline_sensors": [],
        "shift_changeover": False,
    },
    "hot_work_conflict": {
        "description": "Hot work permit active while gas is elevated",
        "gas_base": {"H2S": 4.0, "CO": 20.0, "CH4": 8.0},
        "gas_rate": {"H2S": 0.12, "CO": 0.4, "CH4": 0.2},
        "permits": ["HOT_WORK"],
        "offline_sensors": [],
        "shift_changeover": False,
    },
    "vizag_pattern": {
        "description": "Full Vizag replay: gas + hot work + offline sensor + shift changeover",
        "gas_base": {"H2S": 1.0, "CO": 8.0, "CH4": 3.0},
        "gas_rate": {"H2S": 0.30, "CO": 1.0, "CH4": 0.55},
        "permits": ["HOT_WORK", "CONFINED_SPACE"],
        "offline_sensors": ["G-07"],
        "shift_changeover": True,
    },
}

# ── INCIDENT_SCENARIOS alias — keeps Member 2's backend working ───────────────
INCIDENT_SCENARIOS = {
    name: {
        "description":      cfg["description"],
        "duration_minutes": 120,
        "active_permits":   cfg["permits"],
        "incidents":        [],
        "maintenance_offline": cfg.get("offline_sensors", []),
    }
    for name, cfg in SCENARIO_CONFIGS.items()
}

# ── Plant zones — for Member 2's /zones endpoint ──────────────────────────────
@dataclass
class PlantZone:
    name: str
    description: str
    hazardous_area_class: str
    sensors: List[str]
    x: float
    y: float
    width: float
    height: float

PLANT_ZONES: Dict[str, PlantZone] = {
    "ZONE_A": PlantZone("Battery head", "Coke oven push side", "Zone 1",
                        ["G-01","G-02","G-03"], 0.05, 0.1, 0.28, 0.45),
    "ZONE_B": PlantZone("Collector main", "Gas collection corridor", "Zone 1",
                        ["G-04","G-05","G-06"], 0.37, 0.1, 0.28, 0.45),
    "ZONE_C": PlantZone("Coke side / quench", "Coke discharge — combined gas + heat", "Zone 2",
                        ["G-07","G-08","G-09"], 0.69, 0.1, 0.26, 0.45),
    "CONTROL_ROOM": PlantZone("Control room", "Operations control — safe area", "Safe",
                              ["ENV-01"], 0.05, 0.6, 0.28, 0.35),
    "MAINTENANCE_BAY": PlantZone("Maintenance bay", "Workshop", "Zone 2",
                                 ["G-10","G-11"], 0.37, 0.6, 0.58, 0.35),
}