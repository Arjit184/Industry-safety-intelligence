import React, { useState, useEffect } from "react";

const COLORS = { LOW:"#22c55e", WARNING:"#f59e0b", HIGH:"#f97316", CRITICAL:"#ef4444" };

export default function RiskScore({ assessment }) {
  const risk_score = assessment?.risk_score ?? 0;
  const risk_level = assessment?.risk_level ?? "LOW";
  const previous_score = assessment?.previous_score ?? 0;
  const prediction = assessment?.prediction ?? {};

  const confidence = prediction?.confidence ?? 0;
  const minutes_to_next = prediction?.minutes_to_next_threshold ?? null;
  const next_threshold = prediction?.next_threshold ?? null;
  const lead_time = prediction?.lead_time_advantage_minutes ?? 0;

  const color = COLORS[risk_level] || "#888";
  const diff = risk_score - previous_score;
  const trend = diff > 0 ? `▲ ${diff} pts` : diff < 0 ? `▼ ${Math.abs(diff)} pts` : "— no change";
  const trendColor = diff > 0 ? "#ef4444" : "#22c55e";
  const radius = 60, circ = 2 * Math.PI * radius;
  const offset = circ - (risk_score / 100) * circ;

  const [secondsLeft, setSecondsLeft] = useState(null);

  // Reset timer only when minutes_to_next changes — not every second
  useEffect(() => {
    if (minutes_to_next) {
      setSecondsLeft(minutes_to_next * 60);
    } else {
      setSecondsLeft(null);
    }
  }, [minutes_to_next]);

  // Tick down — depends only on whether timer is active or not
  useEffect(() => {
    if (!secondsLeft || secondsLeft <= 0) {
      if (secondsLeft === 0) setSecondsLeft(null);
      return;
    }
    const interval = setInterval(() => {
      setSecondsLeft(s => s - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [secondsLeft > 0]);

  const formatTime = (secs) => {
    if (!secs) return null;
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s.toString().padStart(2, "0")}s`;
  };

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
        Confidence: {Math.round(confidence * 100)}%
      </p>

      {secondsLeft && (
        <div style={{ background:"#1f2937", borderRadius:8, padding:"8px 12px", marginBottom:10 }}>
          <p style={{ color:"#6b7280", fontSize:10, margin:"0 0 2px", textTransform:"uppercase", letterSpacing:1 }}>
            Time to {next_threshold}
          </p>
          <p style={{ color:"#f59e0b", fontSize:18, fontWeight:700, margin:0 }}>
            ⏱ {formatTime(secondsLeft)}
          </p>
        </div>
      )}

      {risk_level === "CRITICAL" && !secondsLeft && (
        <div style={{ background:"#450a0a", border:"1px solid #dc2626", borderRadius:8, padding:"8px 12px", marginBottom:10 }}>
          <p style={{ color:"#f87171", fontSize:13, margin:0, fontWeight:700 }}>
            🚨 CRITICAL THRESHOLD REACHED
          </p>
        </div>
      )}

      {lead_time > 0 && (
        <div style={{ background:"#052e16", border:"1px solid #16a34a", borderRadius:8, padding:"8px 12px" }}>
          <p style={{ color:"#4ade80", fontSize:13, margin:0, fontWeight:700 }}>
            ⚡ {lead_time} minutes ahead of single-sensor baseline
          </p>
        </div>
      )}
    </div>
  );
}