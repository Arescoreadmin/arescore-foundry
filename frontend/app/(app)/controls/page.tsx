import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BrandHeader } from "@/components/layout/brand-header";
import { fetchUi } from "@/lib/ui-api";

type ControlsResponse = {
  items: Array<{
    id: string;
    name: string;
    status: string;
    remediation: string;
  }>;
};

const fallbackControls: ControlsResponse = { items: [] };

export default async function ControlsPage() {
  let controls = fallbackControls;

  try {
    controls = await fetchUi<ControlsResponse>("/ui/controls?limit=10", { scopes: ["ui:controls:read"] });
  } catch {
    // fallback in non-connected environments.
  }

  return (
    <div className="space-y-6">
      <BrandHeader
        title="Controls & Remediation"
        subtitle="Frostgate invariants mapped to evidence and guided remediation."
      />
      <Card>
        <CardHeader>
          <CardTitle>Controls &amp; Remediation</CardTitle>
          <CardDescription>Invariant proof matrix mapped to evidence and remediation.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {controls.items.length === 0 && <p className="text-sm text-muted-foreground">No controls available.</p>}
          {controls.items.map((control) => (
            <Link
              key={control.id}
              href={`/controls/${control.id}`}
              className="block rounded-xl border border-border/60 bg-background/60 p-4 transition hover:border-accent/60 hover:bg-foreground/5"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold">{control.name}</p>
                  <p className="text-xs text-muted-foreground">{control.remediation}</p>
                </div>
                <Badge variant={control.status === "healthy" ? "default" : "outline"}>{control.status}</Badge>
              </div>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
