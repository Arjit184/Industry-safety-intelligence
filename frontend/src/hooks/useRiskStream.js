import { useState, useEffect } from "react";

const MOCK_SCENARIOS = {
  vizag_pattern: {
    timestamp: "2025-01-12T22:47:00",
    elapsed_minutes: 11,
    risk_score: 93,
    risk_level: "CRITICAL",
    previous_score: 78,
    risk_factors: [
      { factor_id: "gas_sensor_anomaly", active: true, weight: 0.30, contribution: 24,
        description: "Elevated gas detected at: G-07, G-08", regulatory_ref: "OISD-GS-1 Clause 6.3", evidence: ["G-07","G-08"] },
      { factor_id: "permit_gas_conflict", active: true, weight: 0.25, contribution: 20,
        description: "Hot work permit active in gas-affected zone", regulatory_ref: "DGFASLI OM-2023-11", evidence: ["PTW-047"] },
      { factor_id: "confined_space_unchecked", active: true, weight: 0.20, contribution: 16,
        description: "Confined space entry without gas clearance", regulatory_ref: "Factory Act S.36", evidence: [] },
      { factor_id: "shift_changeover_window", active: true, weight: 0.15, contribution: 12,
        description: "Shift handover incomplete", regulatory_ref: "OISD-GS-1 Clause 9.1", evidence: [] },
      { factor_id: "sensor_maintenance_blindspot", active: true, weight: 0.10, contribution: 8,
        description: "G-09 offline — CH4 unmonitored", regulatory_ref: "OISD-GS-1 Clause 6.1", evidence: ["G-09"] },
    ],
    compound_triggers: [
      { trigger_id: "gas_x_hot_work", factors_involved: ["gas_sensor_anomaly","permit_gas_conflict"],
        multiplier: 1.8, description: "Elevated gas + active hot work permit = explosion precursor.",
        historical_match: "INC-003", regulatory_refs: ["OISD-GS-1 Clause 7.1"] }
    ],
    prediction: { minutes_to_next_threshold: null, next_threshold: null, confidence: 0.92,
      basis: "Linear extrapolation over last 6 readings", single_sensor_minutes: 156, lead_time_advantage_minutes: 145 },
    recommended_actions: [
      { priority: 1, action: "SUSPEND hot work permit PTW-047 immediately",
        rationale: "Hot work in gas-affected zone is leading cause of coke oven explosions",
        regulatory_basis: "DGFASLI OM-2023-11 Clause 4.3", zone: "Zone C", time_sensitive: true },
      { priority: 2, action: "Evacuate Zone B and Zone C — 7 workers",
        rationale: "Gas levels at IDLH threshold", regulatory_basis: "Factory Act S.36(1)(a)", zone: "Zone B", time_sensitive: true },
    ],
    rag_context: "Pattern matches Vizag Jan 2025 at 97% confidence. Battery 3 showed identical H2S + CO co-elevation 73 min before explosion.",
    regulatory_violations: ["OISD-GS-1 Clause 7.1", "Factory Act S.36(1)(a)"],
    incident_report_draft: "SAFETY INCIDENT PRELIMINARY REPORT — 12 Jan 2025 22:47...",
    evacuation_triggered: false,
    sensors: {
      "G-07": { sensor_id:"G-07", sensor_type:"H2S", value:19.8, unit:"ppm", status:"IDLH", threshold_warning:5, threshold_critical:10 },
      "G-08": { sensor_id:"G-08", sensor_type:"CO", value:52.1, unit:"ppm", status:"WARNING", threshold_warning:25, threshold_critical:50 },
      "G-09": { sensor_id:"G-09", sensor_type:"CH4", value:null, unit:"% LEL", status:"OFFLINE", threshold_warning:10, threshold_critical:25 },
      "T-01": { sensor_id:"T-01", sensor_type:"TEMP", value:312, unit:"°C", status:"HIGH", threshold_warning:280, threshold_critical:320 },
      "P-01": { sensor_id:"P-01", sensor_type:"PRESSURE", value:4.2, unit:"bar", status:"NORMAL", threshold_warning:5, threshold_critical:6 },
      "G-10": { sensor_id:"G-10", sensor_type:"O2", value:17.1, unit:"%", status:"LOW", threshold_warning:19.5, threshold_critical:16 },
    },
    active_permits: [
      { permit_id:"PTW-047", type:"HOT_WORK", zone:"Zone C", description:"HOT WORK — angle grinding Zone C", risk_flag:true, conflict_reason:"Gas readings exceed safe limit" }
    ],
    shift: { shift:"C", supervisor:"R. Venkatesh", in_changeover_window:true, handover_complete:false,
      workers_in_hazardous_zones:{"Zone A":3,"Zone B":5,"Zone C":2}, fatigue_flag:true,
      notes:"Battery 3 push side showing elevated readings since 21:30" }
  },

  normal_ops: {
    timestamp: "2025-01-12T20:00:00", elapsed_minutes: 0, risk_score: 12, risk_level: "LOW", previous_score: 10,
    risk_factors: [
      { factor_id: "gas_sensor_anomaly", active: false, weight: 0.30, contribution: 0, description: "All gas sensors within normal range", regulatory_ref: "OISD-GS-1 Clause 6.3", evidence: [] },
      { factor_id: "permit_gas_conflict", active: false, weight: 0.25, contribution: 0, description: "No permit conflicts detected", regulatory_ref: "DGFASLI OM-2023-11", evidence: [] },
      { factor_id: "confined_space_unchecked", active: false, weight: 0.20, contribution: 0, description: "All confined space checks complete", regulatory_ref: "Factory Act S.36", evidence: [] },
      { factor_id: "shift_changeover_window", active: false, weight: 0.15, contribution: 0, description: "Shift handover complete", regulatory_ref: "OISD-GS-1 Clause 9.1", evidence: [] },
      { factor_id: "sensor_maintenance_blindspot", active: false, weight: 0.10, contribution: 0, description: "All sensors operational", regulatory_ref: "OISD-GS-1 Clause 6.1", evidence: [] },
    ],
    compound_triggers: [],
    prediction: { minutes_to_next_threshold: 90, next_threshold: "WARNING", confidence: 0.65, basis: "Stable readings", single_sensor_minutes: 90, lead_time_advantage_minutes: 0 },
    recommended_actions: [{ priority: 1, action: "Continue routine monitoring", rationale: "All systems nominal", regulatory_basis: "OISD-GS-1 Clause 5.1", zone: "All", time_sensitive: false }],
    rag_context: null, regulatory_violations: [], incident_report_draft: null, evacuation_triggered: false,
    sensors: {
      "G-07": { sensor_id:"G-07", sensor_type:"H2S", value:1.2, unit:"ppm", status:"NORMAL", threshold_warning:5, threshold_critical:10 },
      "G-08": { sensor_id:"G-08", sensor_type:"CO", value:8.4, unit:"ppm", status:"NORMAL", threshold_warning:25, threshold_critical:50 },
      "G-09": { sensor_id:"G-09", sensor_type:"CH4", value:3.1, unit:"% LEL", status:"NORMAL", threshold_warning:10, threshold_critical:25 },
      "T-01": { sensor_id:"T-01", sensor_type:"TEMP", value:248, unit:"°C", status:"NORMAL", threshold_warning:280, threshold_critical:320 },
      "P-01": { sensor_id:"P-01", sensor_type:"PRESSURE", value:3.1, unit:"bar", status:"NORMAL", threshold_warning:5, threshold_critical:6 },
      "G-10": { sensor_id:"G-10", sensor_type:"O2", value:20.8, unit:"%", status:"NORMAL", threshold_warning:19.5, threshold_critical:16 },
    },
    active_permits: [],
    shift: { shift:"A", supervisor:"K. Ramamurthy", in_changeover_window:false, handover_complete:true,
      workers_in_hazardous_zones:{"Zone A":2,"Zone B":2,"Zone C":1}, fatigue_flag:false, notes:"Normal operations." }
  },

  gas_rising: {
    timestamp: "2025-01-12T21:30:00", elapsed_minutes: 35, risk_score: 42, risk_level: "WARNING", previous_score: 28,
    risk_factors: [
      { factor_id: "gas_sensor_anomaly", active: true, weight: 0.30, contribution: 18, description: "H2S trending upward at G-07", regulatory_ref: "OISD-GS-1 Clause 6.3", evidence: ["G-07"] },
      { factor_id: "permit_gas_conflict", active: false, weight: 0.25, contribution: 0, description: "No active permits in affected zone", regulatory_ref: "DGFASLI OM-2023-11", evidence: [] },
      { factor_id: "confined_space_unchecked", active: false, weight: 0.20, contribution: 0, description: "Confined space checks complete", regulatory_ref: "Factory Act S.36", evidence: [] },
      { factor_id: "shift_changeover_window", active: false, weight: 0.15, contribution: 0, description: "Shift stable", regulatory_ref: "OISD-GS-1 Clause 9.1", evidence: [] },
      { factor_id: "sensor_maintenance_blindspot", active: false, weight: 0.10, contribution: 0, description: "All sensors operational", regulatory_ref: "OISD-GS-1 Clause 6.1", evidence: [] },
    ],
    compound_triggers: [],
    prediction: { minutes_to_next_threshold: 28, next_threshold: "HIGH", confidence: 0.74, basis: "Linear extrapolation", single_sensor_minutes: 28, lead_time_advantage_minutes: 0 },
    recommended_actions: [{ priority: 1, action: "Increase monitoring frequency at G-07", rationale: "H2S trending toward warning threshold", regulatory_basis: "OISD-GS-1 Clause 6.3", zone: "Zone C", time_sensitive: false }],
    rag_context: null, regulatory_violations: [], incident_report_draft: null, evacuation_triggered: false,
    sensors: {
      "G-07": { sensor_id:"G-07", sensor_type:"H2S", value:9.1, unit:"ppm", status:"WARNING", threshold_warning:5, threshold_critical:10 },
      "G-08": { sensor_id:"G-08", sensor_type:"CO", value:19.2, unit:"ppm", status:"NORMAL", threshold_warning:25, threshold_critical:50 },
      "G-09": { sensor_id:"G-09", sensor_type:"CH4", value:5.8, unit:"% LEL", status:"NORMAL", threshold_warning:10, threshold_critical:25 },
      "T-01": { sensor_id:"T-01", sensor_type:"TEMP", value:271, unit:"°C", status:"NORMAL", threshold_warning:280, threshold_critical:320 },
      "P-01": { sensor_id:"P-01", sensor_type:"PRESSURE", value:3.8, unit:"bar", status:"NORMAL", threshold_warning:5, threshold_critical:6 },
      "G-10": { sensor_id:"G-10", sensor_type:"O2", value:19.8, unit:"%", status:"NORMAL", threshold_warning:19.5, threshold_critical:16 },
    },
    active_permits: [],
    shift: { shift:"B", supervisor:"P. Krishnan", in_changeover_window:false, handover_complete:true,
      workers_in_hazardous_zones:{"Zone A":3,"Zone B":4,"Zone C":3}, fatigue_flag:false, notes:"G-07 climbing since 21:15." }
  },

  hot_work_gas: {
    timestamp: "2025-01-12T22:10:00", elapsed_minutes: 55, risk_score: 67, risk_level: "HIGH", previous_score: 51,
    risk_factors: [
      { factor_id: "gas_sensor_anomaly", active: true, weight: 0.30, contribution: 22, description: "Elevated gas at G-07, G-08", regulatory_ref: "OISD-GS-1 Clause 6.3", evidence: ["G-07","G-08"] },
      { factor_id: "permit_gas_conflict", active: true, weight: 0.25, contribution: 18, description: "Hot work permit active in gas zone", regulatory_ref: "DGFASLI OM-2023-11", evidence: ["PTW-047"] },
      { factor_id: "confined_space_unchecked", active: false, weight: 0.20, contribution: 0, description: "Confined space checks complete", regulatory_ref: "Factory Act S.36", evidence: [] },
      { factor_id: "shift_changeover_window", active: true, weight: 0.15, contribution: 10, description: "Shift changeover in progress", regulatory_ref: "OISD-GS-1 Clause 9.1", evidence: [] },
      { factor_id: "sensor_maintenance_blindspot", active: false, weight: 0.10, contribution: 0, description: "All sensors operational", regulatory_ref: "OISD-GS-1 Clause 6.1", evidence: [] },
    ],
    compound_triggers: [
      { trigger_id: "gas_x_hot_work", factors_involved: ["gas_sensor_anomaly","permit_gas_conflict"],
        multiplier: 1.8, description: "Elevated gas + active hot work permit = explosion precursor.",
        historical_match: "INC-003", regulatory_refs: ["OISD-GS-1 Clause 7.1"] }
    ],
    prediction: { minutes_to_next_threshold: 14, next_threshold: "CRITICAL", confidence: 0.83, basis: "Compound trigger acceleration model", single_sensor_minutes: 14, lead_time_advantage_minutes: 0 },
    recommended_actions: [{ priority: 1, action: "SUSPEND hot work permit PTW-047 immediately", rationale: "Gas + hot work = critical explosion risk", regulatory_basis: "DGFASLI OM-2023-11 Clause 4.3", zone: "Zone C", time_sensitive: true }],
    rag_context: "Compound trigger matches pre-incident conditions at Vizag 2025.", regulatory_violations: ["OISD-GS-1 Clause 7.1"],
    incident_report_draft: null, evacuation_triggered: false,
    sensors: {
      "G-07": { sensor_id:"G-07", sensor_type:"H2S", value:14.3, unit:"ppm", status:"IDLH", threshold_warning:5, threshold_critical:10 },
      "G-08": { sensor_id:"G-08", sensor_type:"CO", value:38.7, unit:"ppm", status:"WARNING", threshold_warning:25, threshold_critical:50 },
      "G-09": { sensor_id:"G-09", sensor_type:"CH4", value:8.2, unit:"% LEL", status:"NORMAL", threshold_warning:10, threshold_critical:25 },
      "T-01": { sensor_id:"T-01", sensor_type:"TEMP", value:291, unit:"°C", status:"HIGH", threshold_warning:280, threshold_critical:320 },
      "P-01": { sensor_id:"P-01", sensor_type:"PRESSURE", value:4.6, unit:"bar", status:"NORMAL", threshold_warning:5, threshold_critical:6 },
      "G-10": { sensor_id:"G-10", sensor_type:"O2", value:18.2, unit:"%", status:"LOW", threshold_warning:19.5, threshold_critical:16 },
    },
    active_permits: [
      { permit_id:"PTW-047", type:"HOT_WORK", zone:"Zone C", description:"HOT WORK — angle grinding Zone C", risk_flag:true, conflict_reason:"Gas readings exceed safe limit" }
    ],
    shift: { shift:"C", supervisor:"R. Venkatesh", in_changeover_window:true, handover_complete:false,
      workers_in_hazardous_zones:{"Zone A":3,"Zone B":5,"Zone C":2}, fatigue_flag:true, notes:"Shift changeover in progress. PTW-047 still active." }
  }
};

export function useRiskStream() {
  const [assessment, setAssessment] = useState(MOCK_SCENARIOS.vizag_pattern);
  const [connected, setConnected] = useState(false);
  const [scenario, setScenario] = useState("vizag_pattern");

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/stream/${scenario}`);
    ws.onopen = () => { setConnected(true); };
    ws.onmessage = (e) => { try { setAssessment(JSON.parse(e.data)); } catch(err) {} };
    ws.onerror = () => {
      setConnected(false);
      setAssessment(MOCK_SCENARIOS[scenario] || MOCK_SCENARIOS.vizag_pattern);
    };
    ws.onclose = () => { setConnected(false); };
    return () => ws.close();
  }, [scenario]);

  const handleSetScenario = (s) => {
    setScenario(s);
    if (!connected) setAssessment(MOCK_SCENARIOS[s] || MOCK_SCENARIOS.vizag_pattern);
  };

  return { assessment, connected, scenario, setScenario: handleSetScenario };
}