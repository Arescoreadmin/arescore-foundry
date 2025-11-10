import { Suspense } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { TelemetryStream } from "@/app/(app)/dashboard/telemetry-stream";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <Card className="border-accent/40 bg-gradient-to-br from-background/90 via-background/70 to-accent/5">
        <CardHeader>
          <CardTitle>Telemetry Overview</CardTitle>
          <CardDescription>Live resonance events and frostfield stability samples.</CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<p className="text-sm text-muted-foreground">Binding stream...</p>}>
            <TelemetryStream />
          </Suspense>
        </CardContent>
      </Card>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Runic Forecast</CardTitle>
            <CardDescription>Projected anomaly probability across frost quadrants.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 text-sm text-muted-foreground">
              <div>
                <p className="text-xs uppercase tracking-wider">Northern veil</p>
                <div className="mt-2 h-2 rounded-full bg-foreground/10">
                  <div className="h-2 w-3/4 rounded-full bg-gradient-to-r from-primary to-secondary" />
                </div>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wider">Starwell trench</p>
                <div className="mt-2 h-2 rounded-full bg-foreground/10">
                  <div className="h-2 w-2/3 rounded-full bg-gradient-to-r from-secondary to-accent" />
                </div>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wider">Glaive horizon</p>
                <div className="mt-2 h-2 rounded-full bg-foreground/10">
                  <div className="h-2 w-1/2 rounded-full bg-gradient-to-r from-accent to-primary" />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Rune Narration</CardTitle>
            <CardDescription>Highlights curated for the nightly council sync.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 text-sm text-muted-foreground">
              {[1, 2, 3].map((n) => (
                <div key={n} className="rounded-xl border border-border/60 bg-background/70 p-4">
                  <p className="font-medium text-foreground">Narrative shard {n}</p>
                  <p>Placeholder for the operations scribe to stitch ritual context and actions.</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Gate Pulse Health</CardTitle>
          <CardDescription>Composite metrics for each active gate shard.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-border/50 text-sm text-muted-foreground">
            {["Icelock", "Helsreach", "Frostmere"].map((site) => (
              <div key={site} className="flex flex-wrap items-center justify-between gap-4 py-4">
                <span className="font-medium text-foreground">{site}</span>
                <span className="flex gap-3">
                  <Badge variant="glow">Stability 94%</Badge>
                  <Badge variant="outline">Resonance 82%</Badge>
                  <Badge variant="outline">Anomaly risk 8%</Badge>
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Separator />
    </div>
  );
}
