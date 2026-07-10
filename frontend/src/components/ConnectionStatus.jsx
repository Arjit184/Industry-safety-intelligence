import React from "react";

export function LoadingScreen() {
  return (
    <div
      style={{
        background: "#030712",
        color: "white",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "sans-serif",
      }}
    >
      <h1 style={{ color: "#f97316" }}>⚙ SafetyIQ</h1>
      <p>Connecting to backend...</p>
    </div>
  );
}

export function CachedBanner({ connectionState }) {
  if (connectionState !== "cached") return null;

  return (
    <div
      style={{
        background: "#f59e0b",
        color: "#111827",
        padding: "8px",
        textAlign: "center",
        fontWeight: 600,
      }}
    >
      Backend disconnected • Showing last known assessment
    </div>
  );
}