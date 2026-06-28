import React from "react";

const ZONES = [
  { id:"Zone A", x:30, y:40, w:150, h:110, sensors:["G-10"] },
  { id:"Zone B", x:200, y:40, w:150, h:110, sensors:["G-08","T-01"] },
  { id:"Zone C", x:370, y:40, w:150, h:110, sensors:["G-07","G-09"] },
  { id:"Control Room", x:30, y:175, w:220, h:90, sensors:["P-01"] },
  { id:"Maintenance Bay", x:270, y:175, w:250, h:90, sensors:[] },
];

function getZoneColor(zone, sensors) {
  const statuses = zone.sensors.map(id => sensors[id]?.status);
  if (statuses.includes("IDLH")) return "#7f1d1d";
  if (statuses.includes("OFFLINE")) return "#7f1d1d";
  if (statuses.includes("WARNING") || statuses.includes("HIGH")) return "#78350f";
  if (statuses.includes("LOW")) return "#1e3a5f";
  return "#14532d";
}

export default function PlantMap({ assessment }) {
  const { sensors, active_permits, shift } = assessment;
  const workers = shift.workers_in_hazardous_zones;
  const hotWorkZones = active_permits.filter(p => p.risk_flag).map(p => p.zone);

  return (
    <div style={{ background:"#111827", borderRadius:16, padding:20 }}>
      <p style={{ color:"#6b7280", fontSize:11, margin:"0 0 12px", letterSpacing:2, textTransform:"uppercase" }}>
        Plant Heatmap — Coke Oven Battery 3
      </p>
      <svg width="100%" viewBox="0 0 560 290" style={{ fontFamily:"sans-serif" }}>
        {ZONES.map(zone => {
          const fill = getZoneColor(zone, sensors);
          const workerCount = workers[zone.id] || 0;
          const hasHotWork = hotWorkZones.includes(zone.id);
          return (
            <g key={zone.id}>
              <rect x={zone.x} y={zone.y} width={zone.w} height={zone.h}
                rx="8" fill={fill} stroke="#374151" strokeWidth="1"
                style={{ transition:"fill 0.5s ease" }}/>
              <text x={zone.x+10} y={zone.y+20} fill="white" fontSize="11" fontWeight="600">{zone.id}</text>
              {hasHotWork && <text x={zone.x+zone.w-22} y={zone.y+20} fontSize="13">🔥</text>}
              {zone.sensors.map((sid, i) => {
                const s = sensors[sid];
                if (!s) return null;
                const dotColor = s.status==="OFFLINE"?"#6b7280":s.status==="IDLH"?"#dc2626":s.status==="WARNING"?"#f59e0b":"#22c55e";
                return (
                  <g key={sid}>
                    <circle cx={zone.x+14+(i*30)} cy={zone.y+zone.h-18} r="9" fill={dotColor}/>
                    <text x={zone.x+14+(i*30)} y={zone.y+zone.h-14} textAnchor="middle" fill="white" fontSize="6" fontWeight="700">
                      {s.status==="OFFLINE"?"OFF":sid}
                    </text>
                  </g>
                );
              })}
              {[...Array(workerCount)].map((_,i) => (
                <circle key={i} cx={zone.x+14+(i*14)} cy={zone.y+zone.h-38} r="4" fill="#3b82f6" opacity="0.9"/>
              ))}
            </g>
          );
        })}
      </svg>
      <div style={{ display:"flex", gap:14, marginTop:8, flexWrap:"wrap" }}>
        {[["#14532d","Safe"],["#78350f","Warning"],["#7f1d1d","Critical"],["#3b82f6","Worker"],["#6b7280","Offline"]].map(([c,l])=>(
          <div key={l} style={{ display:"flex", alignItems:"center", gap:5 }}>
            <div style={{ width:10, height:10, borderRadius:"50%", background:c }}/>
            <span style={{ color:"#9ca3af", fontSize:11 }}>{l}</span>
          </div>
        ))}
      </div>
    </div>
  );
}