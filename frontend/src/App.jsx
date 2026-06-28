import React from "react";
import { useRiskStream } from "./hooks/useRiskStream";
import RiskScore from "./components/RiskScore";
import PlantMap from "./components/PlantMap";
import { SensorGrid, PermitPanel, RiskFactors, AlertFeed, ScenarioSwitcher, EvacuateButton } from "./components/index.jsx";

export default function App() {
  const { assessment, connected, scenario, setScenario } = useRiskStream();

  return (
    <div style={{ background:"#030712", minHeight:"100vh", color:"white", fontFamily:"sans-serif", padding:16, boxSizing:"border-box" }}>

      {/* Top bar */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
        <div>
          <h1 style={{ margin:0, fontSize:20, fontWeight:700, color:"#f97316" }}>⚙ SafetyIQ</h1>
          <p style={{ margin:0, fontSize:11, color:"#6b7280" }}>Industrial Safety Intelligence · Vizag Coke Oven Battery 3</p>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <div style={{ width:8, height:8, borderRadius:"50%", background:connected?"#22c55e":"#ef4444" }}/>
          <span style={{ fontSize:11, color:"#9ca3af" }}>{connected?"Live — Backend Connected":"Mock Data"}</span>
        </div>
      </div>

      {/* Scenario buttons */}
      <div style={{ marginBottom:14 }}>
        <ScenarioSwitcher scenario={scenario} setScenario={setScenario}/>
      </div>

      {/* 3 column layout */}
      <div style={{ display:"grid", gridTemplateColumns:"280px 1fr 280px", gap:12 }}>

        {/* LEFT column */}
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <RiskScore assessment={assessment}/>
          <div style={{ background:"#111827", borderRadius:16, padding:16 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 10px", textTransform:"uppercase", letterSpacing:2 }}>Active Permits</p>
            <PermitPanel permits={assessment.active_permits}/>
          </div>
          <div style={{ background:"#111827", borderRadius:16, padding:14 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 8px", textTransform:"uppercase", letterSpacing:2 }}>Shift Info</p>
            <p style={{ color:"white", fontSize:12, margin:"0 0 3px" }}>Shift {assessment.shift.shift} · {assessment.shift.supervisor}</p>
            <p style={{ color:assessment.shift.in_changeover_window?"#f59e0b":"#22c55e", fontSize:11, margin:"0 0 3px" }}>
              {assessment.shift.in_changeover_window?"⚠ Changeover in progress":"✓ Stable"}
            </p>
            <p style={{ color:"#6b7280", fontSize:10, margin:0 }}>{assessment.shift.notes}</p>
          </div>
          <EvacuateButton assessment={assessment}/>
        </div>

        {/* CENTRE column */}
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <PlantMap assessment={assessment}/>
          <div style={{ background:"#111827", borderRadius:16, padding:16 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 12px", textTransform:"uppercase", letterSpacing:2 }}>Live Sensors</p>
            <SensorGrid sensors={assessment.sensors}/>
          </div>
        </div>

        {/* RIGHT column */}
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <div style={{ background:"#111827", borderRadius:16, padding:16 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 10px", textTransform:"uppercase", letterSpacing:2 }}>Risk Factors</p>
            <RiskFactors factors={assessment.risk_factors} compound_triggers={assessment.compound_triggers}/>
          </div>
          <div style={{ background:"#111827", borderRadius:16, padding:16 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 10px", textTransform:"uppercase", letterSpacing:2 }}>Alert Feed</p>
            <AlertFeed actions={assessment.recommended_actions} rag_context={assessment.rag_context} violations={assessment.regulatory_violations}/>
          </div>
        </div>

      </div>
    </div>
  );
}