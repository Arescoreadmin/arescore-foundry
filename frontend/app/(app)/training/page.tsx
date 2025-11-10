import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const drills = [
  {
    name: "Cryoform Cascade",
    status: "Scheduled",
    cadence: "Every 4 hours",
    focus: "Stability harmonics",
  },
  {
    name: "Shard Lattice Weave",
    status: "Active",
    cadence: "Live",
    focus: "Rune resilience",
  },
  {
    name: "Aurora Feedback Loop",
    status: "Cooling",
    cadence: "Completed",
    focus: "Telemetry sync",
  },
];

export default function TrainingPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Training Console</CardTitle>
          <CardDescription>Configure cadet rituals, narrate guidance, and monitor outcomes.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            Each cadence captures FrostGate lore, exercises rune discipline, and calibrates conductor focus. Inject the narrative
            scaffolding your squads need before launching new trials.
          </p>
          <Button className="w-full justify-center md:w-auto">Launch new drill</Button>
        </CardContent>
      </Card>
      <div className="grid gap-6 md:grid-cols-2">
        {drills.map((drill) => (
          <Card key={drill.name} className="border border-border/60 bg-background/70">
            <CardHeader>
              <CardTitle>{drill.name}</CardTitle>
              <CardDescription>{drill.focus}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="flex items-center justify-between">
                <span>Status</span>
                <Badge variant={drill.status === "Active" ? "glow" : "outline"}>{drill.status}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span>Cadence</span>
                <span className="font-medium text-foreground">{drill.cadence}</span>
              </div>
              <Button variant="ghost" className="w-full justify-center text-sm">
                Narrate ritual transcript
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Training Notes</CardTitle>
          <CardDescription>Use this canvas to storyboard upcoming rites and drills.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>Placeholder for scriptwriters to weave story beats, objectives, and resonant dialogues.</p>
          <div className="min-h-[180px] rounded-2xl border border-dashed border-border/60 bg-background/50 p-6">
            Summon your script ideas here...
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
