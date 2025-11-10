import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const segments = [
  {
    name: "Icelock Bastion",
    climate: "Cryo storm",
    wards: 12,
    stability: 92,
  },
  {
    name: "Veilstep Outpost",
    climate: "Aurora flux",
    wards: 8,
    stability: 84,
  },
  {
    name: "Starwell Descent",
    climate: "Grav inversion",
    wards: 14,
    stability: 77,
  },
];

export default function SitesPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Sites & Segments</CardTitle>
          <CardDescription>Map shards, climate effects, and runic wards at a glance.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          {segments.map((segment) => (
            <Card key={segment.name} className="border border-border/60 bg-background/70">
              <CardHeader>
                <CardTitle>{segment.name}</CardTitle>
                <CardDescription>{segment.climate}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <div className="flex items-center justify-between">
                  <span>Wards</span>
                  <span className="font-semibold text-foreground">{segment.wards}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Stability</span>
                  <Badge variant={segment.stability > 85 ? "glow" : "outline"}>{segment.stability}%</Badge>
                </div>
                <p>Placeholder for geo-viz overlays, anomaly tags, and local incidents.</p>
              </CardContent>
            </Card>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Segment Narration</CardTitle>
          <CardDescription>Story beats to contextualize site performance and lore.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>Use this space to chronicle shifts in the frostfield and call out emerging threads.</p>
          <div className="min-h-[160px] rounded-2xl border border-dashed border-border/60 bg-background/50 p-6">
            Narration placeholders awaiting the next lore drop.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
