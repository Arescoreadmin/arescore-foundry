"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { buildMockTelemetry, type TelemetryFrame } from "@/lib/telemetry";

interface TelemetryContextValue {
  frames: TelemetryFrame[];
  status: "connecting" | "streaming" | "offline";
  lastUpdated?: Date;
}

const TelemetryContext = createContext<TelemetryContextValue | undefined>(undefined);

export function TelemetryProvider({ children }: { children: ReactNode }) {
  const [frames, setFrames] = useState<TelemetryFrame[]>([]);
  const [status, setStatus] = useState<TelemetryContextValue["status"]>("connecting");
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function connect() {
      try {
        const sse = new EventSource("/api/telemetry", { withCredentials: true });
        setStatus("connecting");

        sse.onmessage = (event) => {
          const payload = JSON.parse(event.data) as TelemetryFrame;
          setFrames((prev) => [payload, ...prev].slice(0, 50));
          setStatus("streaming");
        };

        sse.onerror = () => {
          sse.close();
          setStatus("offline");
          fallbackToMock();
        };

        controller.signal.addEventListener("abort", () => {
          sse.close();
        });
      } catch (error) {
        console.warn("Telemetry SSE fallback", error);
        fallbackToMock();
      }
    }

    function fallbackToMock() {
      if (timerRef.current) return;
      setStatus("streaming");
      timerRef.current = setInterval(() => {
        setFrames((prev) => [buildMockTelemetry(), ...prev].slice(0, 50));
      }, 2500);
    }

    connect();

    return () => {
      controller.abort();
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const value = useMemo<TelemetryContextValue>(() => ({
    frames,
    status,
    lastUpdated: frames[0] ? new Date(frames[0].timestamp) : undefined,
  }), [frames, status]);

  return <TelemetryContext.Provider value={value}>{children}</TelemetryContext.Provider>;
}

export function useTelemetry() {
  const ctx = useContext(TelemetryContext);

  if (!ctx) {
    throw new Error("useTelemetry must be used inside TelemetryProvider");
  }

  return ctx;
}
