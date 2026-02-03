import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { fetchUi } from "@/lib/ui-api";

type PostureResponse = {
  posture: {
    tiles: { allow: number; deny: number; total: number };
    trends: Array<{ label: string; allow: number; deny: number }>;
    top_denies: Array<[string, number]>;
  };
};

type DecisionResponse = {
  items: Array<{
    id: string;
    created_at: string;
    status: string;
    policy: string;
    reason: string;
  }>;
};

const fallbackPosture: PostureResponse = {
  posture: {
    tiles: { allow: 0, deny: 0, total: 0 },
    trends: [{ label: "last_24h", allow: 0, deny: 0 }],
    top_denies: [],
  },
};

const fallbackDecisions: DecisionResponse = { items: [] };

export default async function PosturePage() {
  let posture = fallbackPosture;
  let decisions = fallbackDecisions;

  try {
    posture = await fetchUi<PostureResponse>("/ui/posture", { scopes: ["ui:posture:read"] });
    decisions = await fetchUi<DecisionResponse>("/ui/decisions?limit=5", { scopes: ["ui:decisions:read"] });
  } catch {
    // Fall back to empty state in non-connected environments.
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Security Posture</CardTitle>
          <CardDescription>Tenant-scoped allow/deny posture with top denial drivers.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-border/60 bg-background/60 p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Allow</p>
            <p className="text-2xl font-semibold">{posture.posture.tiles.allow}</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-background/60 p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Deny</p>
            <p className="text-2xl font-semibold">{posture.posture.tiles.deny}</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-background/60 p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Total</p>
            <p className="text-2xl font-semibold">{posture.posture.tiles.total}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Denial Drivers</CardTitle>
            <CardDescription>Top reasons for policy denials.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {posture.posture.top_denies.length === 0 && (
              <p className="text-sm text-muted-foreground">No denials recorded.</p>
            )}
            {posture.posture.top_denies.map(([reason, count]) => (
              <div key={reason} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{reason}</span>
                <Badge variant="outline">{count}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recent Decisions</CardTitle>
            <CardDescription>Latest enforcement decisions for this tenant.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {decisions.items.length === 0 && <p className="text-sm text-muted-foreground">No decisions found.</p>}
            {decisions.items.map((decision) => (
              <div key={decision.id} className="space-y-1 rounded-xl border border-border/60 p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold">{decision.policy}</span>
                  <Badge variant={decision.status === "deny" ? "destructive" : "default"}>{decision.status}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">{decision.reason}</p>
                <Separator className="my-2" />
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{decision.created_at}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
