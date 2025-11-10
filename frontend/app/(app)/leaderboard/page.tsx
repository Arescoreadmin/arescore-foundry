import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const conductors = [
  {
    name: "Kaia Frostbinder",
    guild: "Aurora Wing",
    resonance: 98,
    streak: 12,
  },
  {
    name: "Riven Shardscale",
    guild: "Vost Vanguard",
    resonance: 95,
    streak: 9,
  },
  {
    name: "Seris Dawnforge",
    guild: "Gateward Chorus",
    resonance: 92,
    streak: 6,
  },
];

export default function LeaderboardPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Conductor Leaderboard</CardTitle>
          <CardDescription>Rank FrostGate elite by resonance mastery and runic streaks.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            Narrative hooks for storytellers to celebrate top conductors, highlight recent feats, and tease upcoming rituals.
            Each entry offers room for lore, achievements, and cross-gate shout-outs.
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Runic Standings</CardTitle>
          <CardDescription>Seed data for rankings and narrative beats.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {conductors.map((conductor, index) => (
            <div
              key={conductor.name}
              className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border/60 bg-background/70 p-4"
            >
              <div>
                <p className="text-xs uppercase tracking-widest text-muted-foreground">#{index + 1}</p>
                <p className="font-semibold text-foreground">{conductor.name}</p>
                <p className="text-xs text-muted-foreground">{conductor.guild}</p>
              </div>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Badge variant="glow">Resonance {conductor.resonance}%</Badge>
                <Badge variant="outline">Streak {conductor.streak}</Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
