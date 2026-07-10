// src/App.jsx — Week 4 final
// Uses connectionState instead of connected boolean
// Shows LoadingScreen while backend wakes up
// Shows CachedBanner when showing last-known data

import React from "react";
import { useRiskStream } from "./hooks/useRiskStream";
import RiskScore from "./components/RiskScore";
import PlantMap from "./components/PlantMap";
import { SensorGrid, PermitPanel, RiskFactors, AlertFeed,
         ScenarioSwitcher, EvacuateButton } from "./components/index.jsx";
import { LoadingScreen, CachedBanner } from "./components/ConnectionStatus";

export default function App() {
  const { assessment, connectionState, connected, scenario, setScenario } = useRiskStream();

  // Show loading screen while backend is waking up and we have no data yet
  if (!assessment) {
    return <LoadingScreen />;
  }

  return (
    <div style={{ background:"#030712", minHeight:"100vh", color:"white",
                  fontFamily:"sans-serif", boxSizing:"border-box" }}>

      {/* Cached data warning banner — shows above everything */}
      <CachedBanner connectionState={connectionState} />

      {/* Top bar */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                    padding:"10px 16px", borderBottom:"1px solid #111827" }}>
        <div>
          <h1 style={{ margin:0, fontSize:20, fontWeight:700, color:"#f97316" }}>⚙ SafetyIQ</h1>
          <p style={{ margin:0, fontSize:11, color:"#6b7280" }}>
            Industrial Safety Intelligence · Vizag Coke Oven Battery 3
          </p>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <div style={{
            width:8, height:8, borderRadius:"50%",
            background: connectionState === "LIVE"       ? "#22c55e"
                      : connectionState === "CACHED"     ? "#f59e0b"
                      : connectionState === "CONNECTING" ? "#3b82f6"
                      : "#6b7280",
            animation: "pulse 1.5s infinite",
          }}/>
          <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}`}</style>
          <span style={{ fontSize:11, color:"#9ca3af" }}>
            { connectionState === "LIVE"       ? "Live — Backend Connected"
            : connectionState === "CACHED"     ? "Reconnecting..."
            : connectionState === "CONNECTING" ? "Connecting..."
            : "Waking up..." }
          </span>
        </div>
      </div>

      {/* Scenario buttons */}
      <div style={{ padding:"10px 16px", borderBottom:"1px solid #111827" }}>
        <ScenarioSwitcher scenario={scenario} setScenario={setScenario}/>
      </div>

      {/* Main 3-column layout */}
      <div style={{ display:"grid", gridTemplateColumns:"280px 1fr 280px",
                    gap:12, padding:16 }}>

        {/* LEFT */}
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <RiskScore assessment={assessment}/>
          <div style={{ background:"#111827", borderRadius:16, padding:16 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 10px",
                        textTransform:"uppercase", letterSpacing:2 }}>Active Permits</p>
            <PermitPanel permits={assessment.active_permits}/>
          </div>
          <div style={{ background:"#111827", borderRadius:16, padding:14 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 8px",
                        textTransform:"uppercase", letterSpacing:2 }}>Shift Info</p>
            <p style={{ color:"white", fontSize:12, margin:"0 0 3px" }}>
              Shift {assessment.shift.shift} · {assessment.shift.supervisor}
            </p>
            <p style={{ color:assessment.shift.in_changeover_window?"#f59e0b":"#22c55e",
                        fontSize:11, margin:"0 0 3px" }}>
              {assessment.shift.in_changeover_window ? "⚠ Changeover in progress" : "✓ Stable"}
            </p>
            <p style={{ color:"#6b7280", fontSize:10, margin:0 }}>{assessment.shift.notes}</p>
          </div>
          <EvacuateButton assessment={assessment}/>
        </div>

        {/* CENTRE */}
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <PlantMap assessment={assessment}/>
          <div style={{ background:"#111827", borderRadius:16, padding:16 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 12px",
                        textTransform:"uppercase", letterSpacing:2 }}>Live Sensors</p>
            <SensorGrid sensors={assessment.sensors}/>
          </div>
        </div>

        {/* RIGHT */}
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <div style={{ background:"#111827", borderRadius:16, padding:16 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 10px",
                        textTransform:"uppercase", letterSpacing:2 }}>Risk Factors</p>
            <RiskFactors
              factors={assessment.risk_factors}
              compound_triggers={assessment.compound_triggers}/>
          </div>
          <div style={{ background:"#111827", borderRadius:16, padding:16 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 10px",
                        textTransform:"uppercase", letterSpacing:2 }}>Alert Feed</p>
            <AlertFeed
              actions={assessment.recommended_actions}
              rag_context={assessment.rag_context}
              violations={assessment.regulatory_violations}
              nl_alert={assessment.nl_alert}
            />
          </div>
        </div>

      </div>
    </div>
  );
}