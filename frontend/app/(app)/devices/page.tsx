import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const devices = [
  {
    id: "FG-02X-14",
    role: "Sentinel Relay",
    firmware: "v3.9.1",
    status: "Aligned",
  },
  {
    id: "FG-07V-88",
    role: "Pulse Anchor",
    firmware: "v4.0.0-beta",
    status: "Calibration needed",
  },
  {
    id: "FG-11S-42",
    role: "Spectral Loom",
    firmware: "v3.7.4",
    status: "Aligned",
  },
];

export default function DevicesPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Device Roster</CardTitle>
          <CardDescription>Inspect rune conduits, apply firmware, and monitor status pulses.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            Devices sync through the FrostGate mesh every few minutes. Narration placeholders here will house diagnostics,
            alerts, and orchestrated remediation steps.
          </p>
          <Button variant="outline" className="w-full justify-center md:w-auto">
            Sync guardians
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Pulse Diagnostics</CardTitle>
          <CardDescription>Firmware posture, calibration windows, and rune telemetry.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          {devices.map((device) => (
            <div
              key={device.id}
              className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border/60 bg-background/70 p-4"
            >
              <div>
                <p className="font-semibold text-foreground">{device.id}</p>
                <p>{device.role}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="outline">{device.firmware}</Badge>
                <Badge variant={device.status === "Aligned" ? "glow" : "outline"}>{device.status}</Badge>
                <Button size="sm" variant="ghost">
                  Open details
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
