import { useState, useEffect, useRef, useCallback } from "react";

const WS_BASE =
  window.location.hostname === "localhost"
    ? "ws://localhost:8000"
    : "wss://your-app.onrender.com";

export function useRiskStream() {
  const [assessment,      setAssessment]      = useState(null);
  const [connectionState, setConnectionState] = useState("LOADING");
  const [scenario,        setScenario]        = useState("vizag_pattern");

  // Refs — never cause re-renders
  const wsRef           = useRef(null);
  const reconnectTimer  = useRef(null);
  const reconnectDelay  = useRef(2000);
  const lastGoodData    = useRef(null);   // ← cache of last live assessment
  const shouldConnect   = useRef(true);
  const scenarioRef     = useRef(scenario);

  useEffect(() => { scenarioRef.current = scenario; }, [scenario]);

  const connect = useCallback(() => {
    if (!shouldConnect.current) return;

    // ── Kill the old socket before opening a new one ──────────────────────
    if (wsRef.current) {
      wsRef.current.onclose = null;   // prevent the old onclose from firing
      wsRef.current.close();
    }

    const ws = new WebSocket(
      `${WS_BASE}/ws/stream/${scenarioRef.current}`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectDelay.current = 2000;
      setConnectionState("CONNECTING"); // connected but no message yet
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === "scenario_complete") { ws.close(); return; }
        if (data.type)                          { return; }  // ignore other control msgs

        // ── Got real data — cache it, show it ─────────────────────────────
        lastGoodData.current = data;
        setAssessment(data);
        setConnectionState("LIVE");
      } catch (_) {}
    };

    ws.onerror = () => {
      // onclose fires right after — handle everything there
    };

    ws.onclose = () => {
      if (!shouldConnect.current) return;

      if (lastGoodData.current) {
        // ── Had live data before — show cached, don't touch mock ──────────
        setConnectionState("CACHED");
        // DO NOT call setAssessment here — keep showing last good frame
      } else {
        // ── Never had live data — still loading ───────────────────────────
        setConnectionState("LOADING");
      }

      // Exponential backoff — 2s → 4s → 8s → 30s max
      const delay = Math.min(reconnectDelay.current, 30000);
      reconnectDelay.current = Math.min(delay * 1.5, 30000);
      reconnectTimer.current = setTimeout(connect, delay);
    };

  }, []); // ← empty deps — uses refs, never re-creates

  // Mount / unmount
  useEffect(() => {
    shouldConnect.current = true;
    connect();
    return () => {
      shouldConnect.current = false;
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);

  // Scenario switch
  const handleSetScenario = useCallback((s) => {
    scenarioRef.current    = s;
    lastGoodData.current   = null;   // clear cache — new scenario
    reconnectDelay.current = 2000;   // reset backoff
    setScenario(s);
    setAssessment(null);
    setConnectionState("LOADING");
    clearTimeout(reconnectTimer.current);
    connect();
  }, [connect]);

  return {
    assessment,                              // null = loading, object = data available
    connectionState,                         // "LOADING"|"CONNECTING"|"LIVE"|"CACHED"
    connected: connectionState === "LIVE",
    scenario,
    setScenario: handleSetScenario,
  };
}