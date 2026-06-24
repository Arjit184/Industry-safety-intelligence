"""
SafetyIQ — central config
All sensor thresholds, zone definitions, and scenario parameters live here.
Change numbers here to tune the risk engine without touching agent code.
"""

from dataclasses import dataclass, field
from typing import Dict, List

# ── Sensor thresholds ──────────────────────────────────────────────────────────
# Based on OISD-GS-1, DGMS standards, and Factory Act Schedule
# TWA = time-weighted average (8-hr exposure limit)
# STEL = short-term exposure limit (15-min)
# IDLH = immediately dangerous to life and health

@dataclass
class SensorThreshold:
    unit: str
    normal_max: float      # green zone ceiling
    warning: float         # amber zone — elevated monitoring
    critical: float        # red zone — intervention required
    idlh: float            # evacuate immediately
    twa_limit: float       # regulatory TWA (OISD/Factory Act)
    description: str
    regulatory_ref: str

SENSOR_THRESHOLDS: Dict[str, SensorThreshold] = {
    "H2S": SensorThreshold(
        unit="ppm",
        normal_max=1.0,
        warning=5.0,
        critical=10.0,
        idlh=50.0,
        twa_limit=1.0,
        description="Hydrogen sulphide — coke oven byproduct, heavier than air",
        regulatory_ref="OISD-GS-1 Clause 6.3, Factory Act Schedule 2"
    ),
    "CO": SensorThreshold(
        unit="ppm",
        normal_max=10.0,
        warning=25.0,
        critical=50.0,
        idlh=1200.0,
        twa_limit=20.0,
        description="Carbon monoxide — combustion product, odourless",
        regulatory_ref="OISD-GS-1 Clause 6.4, DGFASLI Guidelines"
    ),
    "CH4": SensorThreshold(
        unit="%LEL",
        normal_max=5.0,
        warning=10.0,
        critical=20.0,
        idlh=40.0,
        twa_limit=5.0,
        description="Methane — lower explosive limit percentage",
        regulatory_ref="OISD-GS-1 Clause 5.2, Factory Act S.36"
    ),
    "O2": SensorThreshold(
        unit="%",
        normal_max=23.5,
        warning=19.5,     # O2 is inverse — LOW is dangerous
        critical=17.0,
        idlh=16.0,
        twa_limit=19.5,
        description="Oxygen — deficiency risk in confined spaces",
        regulatory_ref="Factory Act S.36(1), DGMS Circular 2019"
    ),
    "TEMP": SensorThreshold(
        unit="°C",
        normal_max=45.0,
        warning=55.0,
        critical=65.0,
        idlh=80.0,
        twa_limit=45.0,
        description="Ambient temperature near coke battery",
        regulatory_ref="Factory Act S.13, OISD-STD-105"
    ),
    "PRESSURE": SensorThreshold(
        unit="kPa",
        normal_max=4.0,
        warning=7.0,
        critical=10.0,
        idlh=15.0,
        twa_limit=4.0,
        description="Gas pressure in coke oven collector main",
        regulatory_ref="OISD-GS-1 Clause 7.1"
    ),
}

# ── Plant zones ────────────────────────────────────────────────────────────────
@dataclass
class PlantZone:
    name: str
    description: str
    hazardous_area_class: str   # IEC 60079 zone classification
    sensors: List[str]          # which sensors cover this zone
    x: float                    # for UI heatmap (0–1 normalised)
    y: float
    width: float
    height: float

PLANT_ZONES: Dict[str, PlantZone] = {
    "ZONE_A": PlantZone(
        name="Battery head",
        description="Coke oven battery push side — primary H2S exposure zone",
        hazardous_area_class="Zone 1",
        sensors=["G-01", "G-02", "G-03"],
        x=0.05, y=0.1, width=0.28, height=0.45,
    ),
    "ZONE_B": PlantZone(
        name="Collector main",
        description="Gas collection corridor — highest pressure risk",
        hazardous_area_class="Zone 1",
        sensors=["G-04", "G-05", "G-06"],
        x=0.37, y=0.1, width=0.28, height=0.45,
    ),
    "ZONE_C": PlantZone(
        name="Coke side / quench",
        description="Coke discharge and quench — combined gas + heat hazard",
        hazardous_area_class="Zone 2",
        sensors=["G-07", "G-08", "G-09"],
        x=0.69, y=0.1, width=0.26, height=0.45,
    ),
    "CONTROL_ROOM": PlantZone(
        name="Control room",
        description="Operations control — safe area",
        hazardous_area_class="Safe",
        sensors=["ENV-01"],
        x=0.05, y=0.6, width=0.28, height=0.35,
    ),
    "MAINTENANCE_BAY": PlantZone(
        name="Maintenance bay",
        description="Workshop and equipment storage",
        hazardous_area_class="Zone 2",
        sensors=["G-10", "G-11"],
        x=0.37, y=0.6, width=0.58, height=0.35,
    ),
}

# ── Compound risk weights ──────────────────────────────────────────────────────
# How much each factor contributes to the compound risk score
# These are starting weights — tune these based on your demo scenarios

RISK_WEIGHTS = {
    "gas_sensor_anomaly": 0.30,       # any gas above warning threshold
    "permit_gas_conflict": 0.35,      # hot work permit + elevated gas (most dangerous combo)
    "confined_space_unchecked": 0.20, # confined space entry without pre-entry gas check
    "shift_changeover_window": 0.08,  # risk spikes during handover (cognitive load)
    "sensor_maintenance_blindspot": 0.07,  # detector offline = you're flying blind
}

# Multipliers applied when factors co-occur (compound effect)
COMPOUND_MULTIPLIERS = {
    ("gas_sensor_anomaly", "permit_gas_conflict"): 1.8,     # Vizag-type scenario
    ("confined_space_unchecked", "gas_sensor_anomaly"): 1.6,
    ("sensor_maintenance_blindspot", "gas_sensor_anomaly"): 1.4,
}

# ── Incident scenarios for simulation ─────────────────────────────────────────
# These are baked-in test scenarios your demo will replay.
# Each scenario has a timeline (minutes) with sensor values at each point.

INCIDENT_SCENARIOS = {
    "normal_ops": {
        "description": "Normal coke oven operations, all systems nominal",
        "duration_minutes": 60,
        "base_values": {"H2S": 1.2, "CO": 8.0, "CH4": 3.0, "O2": 20.8, "TEMP": 38.0, "PRESSURE": 2.1},
        "noise_factor": 0.05,
        "active_permits": [],
        "incidents": [],
    },
    "gas_rising": {
        "description": "H2S trending upward — single sensor approaching threshold",
        "duration_minutes": 90,
        "base_values": {"H2S": 2.0, "CO": 15.0, "CH4": 5.0, "O2": 20.5, "TEMP": 41.0, "PRESSURE": 3.2},
        "drift": {"H2S": 0.08, "CO": 0.2, "PRESSURE": 0.04},  # per minute
        "noise_factor": 0.08,
        "active_permits": ["PTW-041: Electrical maintenance Zone B"],
        "incidents": [],
    },
    "hot_work_conflict": {
        "description": "Hot work permit active + gas rising — compound risk scenario",
        "duration_minutes": 120,
        "base_values": {"H2S": 5.0, "CO": 30.0, "CH4": 10.0, "O2": 20.1, "TEMP": 46.0, "PRESSURE": 5.5},
        "drift": {"H2S": 0.12, "CO": 0.5, "CH4": 0.15, "PRESSURE": 0.06},
        "noise_factor": 0.10,
        "active_permits": [
            "PTW-041: Electrical maintenance Zone B",
            "PTW-047: HOT WORK — angle grinding Zone C",  # the dangerous one
        ],
        "incidents": [
            {"at_minute": 47, "type": "compound_risk_alert", "message": "Compound risk threshold breached"}
        ],
    },
    "vizag_pattern": {
        "description": "Full Vizag Jan 2025 precursor pattern — all 5 risk factors active",
        "duration_minutes": 180,
        "base_values": {"H2S": 8.0, "CO": 55.0, "CH4": 18.0, "O2": 19.4, "TEMP": 52.0, "PRESSURE": 8.2},
        "drift": {"H2S": 0.18, "CO": 0.8, "CH4": 0.22, "O2": -0.04, "PRESSURE": 0.09},
        "noise_factor": 0.12,
        "active_permits": [
            "PTW-047: HOT WORK — angle grinding Zone C (CONFLICT WITH GAS READINGS)",
            "PTW-051: Confined space entry Zone B (NO PRE-ENTRY GAS CHECK LOGGED)",
            "PTW-038: Electrical maintenance Zone B",
        ],
        "maintenance_offline": ["G-09"],  # sensor under maintenance = blind spot
        "incidents": [
            {"at_minute": 11, "type": "compound_risk_critical", "message": "CRITICAL: Evacuate Zone B and Zone C"},
            {"at_minute": 156, "type": "single_sensor_alert", "message": "Single sensor H2S threshold breach (baseline comparison)"},
        ],
    },
}