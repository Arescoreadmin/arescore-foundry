"use client";

import { Badge } from "@/components/ui/badge";
import { useTelemetry } from "@/context/telemetry-context";

export function TelemetryStream() {
  const { frames } = useTelemetry();

  return (
    <ul className="space-y-3 text-sm text-muted-foreground">
      {frames.slice(0, 10).map((frame) => (
        <li
          key={frame.id}
          className="flex items-center justify-between rounded-xl border border-border/60 bg-background/70 px-4 py-3"
        >
          <span className="flex items-center gap-3">
            <span className="text-xl font-semibold text-foreground">{frame.glyph}</span>
            <span>
              <span className="font-medium text-foreground">{frame.location}</span>
              <p className="text-xs text-muted-foreground">{new Date(frame.timestamp).toLocaleTimeString()}</p>
            </span>
          </span>
          <span className="flex items-center gap-4">
            <Badge variant="glow">{frame.resonance}% resonance</Badge>
            <Badge variant="outline">{frame.stability}% stability</Badge>
          </span>
        </li>
      ))}
      {frames.length === 0 && <li className="text-muted-foreground">Awaiting first rune pulse...</li>}
    </ul>
  );
}
