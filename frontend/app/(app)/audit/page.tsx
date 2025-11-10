import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const glyphs = [
  {
    id: "AUD-2194",
    actor: "Shardwright",
    scope: "Veilstep",
    status: "Investigating",
    message: "Unexpected resonance spike detected.",
  },
  {
    id: "AUD-2195",
    actor: "Conduit",
    scope: "Starwell",
    status: "Resolved",
    message: "Calibration drift auto-corrected.",
  },
  {
    id: "AUD-2196",
    actor: "Archivist",
    scope: "Icelock",
    status: "Streaming",
    message: "Telemetry stream opened for council review.",
  },
];

export default function AuditPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Audit Viewer</CardTitle>
          <CardDescription>Trace glyph events, annotate anomalies, and narrate follow-ups.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            This viewer pulls from live SSE/WebSocket streams. Placeholder narration reveals where the audit team will drop
            lore snippets, remediation notes, and tags for future investigation.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Glyph Stream</CardTitle>
          <CardDescription>Recent audit glyphs awaiting council narration.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {glyphs.map((glyph) => (
            <div key={glyph.id} className="space-y-2 rounded-xl border border-border/60 bg-background/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
                <span className="font-semibold text-foreground">{glyph.id}</span>
                <span className="flex gap-2">
                  <Badge variant="outline">{glyph.actor}</Badge>
                  <Badge variant="outline">{glyph.scope}</Badge>
                  <Badge variant={glyph.status === "Resolved" ? "default" : "glow"}>{glyph.status}</Badge>
                </span>
              </div>
              <Separator />
              <p className="text-sm text-muted-foreground">{glyph.message}</p>
              <div className="rounded-lg border border-dashed border-border/60 p-3 text-xs text-muted-foreground">
                Narration placeholder for audit notes, transcription, and lore threads.
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
