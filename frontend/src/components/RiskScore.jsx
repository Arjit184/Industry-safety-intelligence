import React from "react";

const COLORS = { LOW:"#22c55e", WARNING:"#f59e0b", HIGH:"#f97316", CRITICAL:"#ef4444" };

export default function RiskScore({ assessment }) {
  const { risk_score, risk_level, previous_score, prediction } = assessment;
  const color = COLORS[risk_level] || "#888";
  const diff = risk_score - previous_score;
  const trend = diff > 0 ? `▲ ${diff} pts` : diff < 0 ? `▼ ${Math.abs(diff)} pts` : "— no change";
  const trendColor = diff > 0 ? "#ef4444" : "#22c55e";
  const radius = 60, circ = 2 * Math.PI * radius;
  const offset = circ - (risk_score / 100) * circ;

  return (
    <div style={{ background:"#111827", borderRadius:16, padding:20, textAlign:"center",
      border:`1px solid ${risk_level==="CRITICAL"?"#dc2626":"#1f2937"}`,
      animation: risk_level==="CRITICAL" ? "cpulse 1.5s ease-in-out infinite" : "none" }}>
      <style>{`@keyframes cpulse{0%,100%{box-shadow:0 0 0 0 rgba(220,38,38,0.4)}50%{box-shadow:0 0 0 14px rgba(220,38,38,0)}}`}</style>
      <p style={{ color:"#6b7280", fontSize:11, margin:"0 0 10px", letterSpacing:2, textTransform:"uppercase" }}>
        Compound Risk Score
      </p>
      <svg width="160" height="160" viewBox="0 0 160 160" style={{ display:"block", margin:"0 auto" }}>
        <circle cx="80" cy="80" r={radius} fill="none" stroke="#1f2937" strokeWidth="14"/>
        <circle cx="80" cy="80" r={radius} fill="none" stroke={color} strokeWidth="14"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          transform="rotate(-90 80 80)" style={{ transition:"all 0.6s ease" }}/>
        <text x="80" y="74" textAnchor="middle" fill="white" fontSize="36" fontWeight="700" fontFamily="sans-serif">{risk_score}</text>
        <text x="80" y="98" textAnchor="middle" fill={color} fontSize="12" fontWeight="600" fontFamily="sans-serif">{risk_level}</text>
      </svg>
      <p style={{ color:trendColor, fontSize:12, margin:"8px 0 2px", fontWeight:600 }}>{trend}</p>
      <p style={{ color:"#6b7280", fontSize:11, margin:"0 0 10px" }}>
        Confidence: {Math.round(prediction.confidence * 100)}%
      </p>
      {prediction.lead_time_advantage_minutes > 0 && (
        <div style={{ background:"#052e16", border:"1px solid #16a34a", borderRadius:8, padding:"8px 12px" }}>
          <p style={{ color:"#4ade80", fontSize:13, margin:0, fontWeight:700 }}>
            ⚡ {prediction.lead_time_advantage_minutes}m ahead of single-sensor baseline
          </p>
        </div>
      )}
    </div>
  );
}