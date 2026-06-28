import React, { useState } from "react";

const STATUS_COLOR = { IDLH:"#dc2626", WARNING:"#f59e0b", OFFLINE:"#6b7280", HIGH:"#f97316", LOW:"#3b82f6", NORMAL:"#22c55e" };

export function SensorGrid({ sensors }) {
  return (
    <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8 }}>
      {Object.values(sensors).map(s => {
        const pct = s.value ? Math.min((s.value / s.threshold_critical) * 100, 100) : 0;
        return (
          <div key={s.sensor_id} style={{ background:"#1f2937", borderRadius:8, padding:10, opacity:s.status==="OFFLINE"?0.5:1 }}>
            <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 3px", textTransform:"uppercase" }}>{s.sensor_id} · {s.sensor_type}</p>
            <p style={{ color:"white", fontSize:18, fontWeight:700, margin:"0 0 4px" }}>
              {s.value ?? "—"} <span style={{ fontSize:10, fontWeight:400, color:"#9ca3af" }}>{s.unit}</span>
            </p>
            <div style={{ background:"#374151", borderRadius:4, height:4, marginBottom:6 }}>
              <div style={{ width:`${pct}%`, height:"100%", borderRadius:4, background:STATUS_COLOR[s.status]||"#888", transition:"width 0.4s" }}/>
            </div>
            <span style={{ background:(STATUS_COLOR[s.status]||"#888")+"22", color:STATUS_COLOR[s.status]||"#888", fontSize:9, padding:"2px 6px", borderRadius:4, fontWeight:700 }}>
              {s.status}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function PermitPanel({ permits }) {
  if (permits.length === 0) return <p style={{ color:"#6b7280", fontSize:12 }}>No active permits</p>;
  return (
    <div>
      {permits.map(p => (
        <div key={p.permit_id} style={{ background:"#1f2937", borderRadius:8, padding:12, marginBottom:8,
          borderLeft:`3px solid ${p.risk_flag?"#dc2626":"#374151"}` }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <span style={{ color:"white", fontWeight:700, fontSize:12 }}>{p.permit_id}</span>
            {p.risk_flag && <span style={{ color:"#dc2626", fontSize:11, fontWeight:700 }}>⚠ CONFLICT</span>}
          </div>
          <p style={{ color:"#9ca3af", fontSize:11, margin:"3px 0 0" }}>{p.description}</p>
          {p.conflict_reason && <p style={{ color:"#f87171", fontSize:10, margin:"3px 0 0" }}>{p.conflict_reason}</p>}
        </div>
      ))}
    </div>
  );
}

export function RiskFactors({ factors, compound_triggers }) {
  return (
    <div>
      {factors.map(f => (
        <div key={f.factor_id} style={{ display:"flex", gap:10, marginBottom:10, alignItems:"flex-start" }}>
          <div style={{ width:8, height:8, borderRadius:"50%", marginTop:4, flexShrink:0,
            background:f.active?"#f97316":"#374151", boxShadow:f.active?"0 0 6px #f97316":"none" }}/>
          <div style={{ flex:1 }}>
            <div style={{ display:"flex", justifyContent:"space-between" }}>
              <span style={{ color:f.active?"white":"#6b7280", fontSize:11 }}>{f.description}</span>
              <span style={{ color:f.active?"#f97316":"#374151", fontSize:11, fontWeight:700, marginLeft:8 }}>
                {f.active?`+${f.contribution}`:"0"}
              </span>
            </div>
            <p style={{ color:"#4b5563", fontSize:9, margin:"2px 0 0" }}>{f.regulatory_ref}</p>
          </div>
        </div>
      ))}
      {compound_triggers.map(t => (
        <div key={t.trigger_id} style={{ background:"#1c1917", border:"1px solid #dc2626", borderRadius:8, padding:10, marginTop:6 }}>
          <p style={{ color:"#f87171", fontSize:11, fontWeight:700, margin:"0 0 3px" }}>⚡ COMPOUND × {t.multiplier}</p>
          <p style={{ color:"#fca5a5", fontSize:10, margin:0 }}>{t.description}</p>
          <p style={{ color:"#6b7280", fontSize:9, margin:"4px 0 0" }}>{t.regulatory_refs.join(", ")}</p>
        </div>
      ))}
    </div>
  );
}

export function AlertFeed({ actions, rag_context, violations }) {
  return (
    <div>
      {actions.map((a,i) => (
        <div key={i} style={{ background:"#1f2937", borderRadius:8, padding:10, marginBottom:8,
          border:`1px solid ${a.time_sensitive?"#dc2626":"#374151"}` }}>
          <div style={{ display:"flex", gap:8, alignItems:"flex-start" }}>
            {a.time_sensitive && <div style={{ width:7, height:7, borderRadius:"50%", background:"#dc2626", marginTop:3, flexShrink:0 }}/>}
            <div>
              <p style={{ color:"white", fontSize:11, fontWeight:600, margin:"0 0 2px" }}>{a.action}</p>
              <p style={{ color:"#6b7280", fontSize:10, margin:0 }}>{a.regulatory_basis} · {a.zone}</p>
            </div>
          </div>
        </div>
      ))}
      {rag_context && (
        <div style={{ background:"#1e1b4b", border:"1px solid #4c1d95", borderRadius:8, padding:10, marginTop:6 }}>
          <p style={{ color:"#a78bfa", fontSize:10, margin:"0 0 3px", fontWeight:700 }}>🔍 HISTORICAL MATCH</p>
          <p style={{ color:"#c4b5fd", fontSize:10, margin:0 }}>{rag_context}</p>
        </div>
      )}
      {violations.length > 0 && (
        <div style={{ marginTop:8, display:"flex", flexWrap:"wrap", gap:4 }}>
          {violations.map((v,i) => (
            <span key={i} style={{ background:"#7f1d1d", color:"#fca5a5", fontSize:9, padding:"2px 6px", borderRadius:4 }}>{v}</span>
          ))}
        </div>
      )}
    </div>
  );
}

export function ScenarioSwitcher({ scenario, setScenario }) {
  const options = [
    { id:"normal_ops",    label:"Normal ops",     color:"#22c55e" },
    { id:"gas_rising",    label:"Gas rising",     color:"#f59e0b" },
    { id:"hot_work_gas",  label:"Hot work + gas", color:"#f97316" },
    { id:"vizag_pattern", label:"Vizag pattern",  color:"#dc2626" },
  ];
  return (
    <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
      {options.map(o => (
        <button key={o.id} onClick={() => setScenario(o.id)} style={{
          padding:"6px 14px", borderRadius:8, border:`1px solid ${o.color}`,
          background: scenario===o.id ? o.color+"33" : "transparent",
          color:o.color, fontSize:12, fontWeight:700, cursor:"pointer"
        }}>{o.label}</button>
      ))}
    </div>
  );
}

export function EvacuateButton({ assessment }) {
  const [showModal, setShowModal] = useState(false);
  const active = assessment.risk_level === "CRITICAL";
  return (
    <>
      <button onClick={() => active && setShowModal(true)} style={{
        width:"100%", padding:14, borderRadius:10, fontWeight:700, fontSize:15,
        cursor:active?"pointer":"not-allowed", border:"none", color:"white",
        background:active?"#dc2626":"#374151",
        animation:active?"epulse 1.5s ease-in-out infinite":"none"
      }}>
        <style>{`@keyframes epulse{0%,100%{box-shadow:0 0 0 0 rgba(220,38,38,0.5)}50%{box-shadow:0 0 0 12px rgba(220,38,38,0)}}`}</style>
        🚨 EVACUATE
      </button>
      {showModal && (
        <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.85)", display:"flex",
          alignItems:"center", justifyContent:"center", zIndex:1000 }}>
          <div style={{ background:"#111827", border:"2px solid #dc2626", borderRadius:16, padding:28, maxWidth:380, width:"90%" }}>
            <p style={{ color:"#dc2626", fontSize:17, fontWeight:700, margin:"0 0 14px" }}>🚨 Evacuation Triggered</p>
            <p style={{ color:"white", fontSize:13, margin:"0 0 6px" }}>✅ All zone supervisors alerted via WhatsApp</p>
            <p style={{ color:"white", fontSize:13, margin:"0 0 6px" }}>✅ PTW-047 auto-suspended</p>
            <p style={{ color:"white", fontSize:13, margin:"0 0 6px" }}>✅ DGFASLI incident report generated</p>
            <p style={{ color:"white", fontSize:13, margin:"0 0 16px" }}>✅ Emergency services notified</p>
            <div style={{ background:"#052e16", border:"1px solid #16a34a", borderRadius:8, padding:10, marginBottom:16 }}>
              <p style={{ color:"#4ade80", fontSize:13, margin:0, fontWeight:700 }}>⚡ 145 minutes ahead of single-sensor baseline</p>
              <p style={{ color:"#86efac", fontSize:11, margin:"4px 0 0" }}>On 12 Jan 2025, these 145 minutes did not exist. 8 workers died.</p>
            </div>
            <button onClick={() => setShowModal(false)} style={{
              background:"#374151", color:"white", border:"none", borderRadius:8,
              padding:"8px 20px", cursor:"pointer", fontWeight:600
            }}>Close</button>
          </div>
        </div>
      )}
    </>
  );
}