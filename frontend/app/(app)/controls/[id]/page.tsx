import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BrandHeader } from "@/components/layout/brand-header";
import { fetchUi } from "@/lib/ui-api";

type ControlResponse = {
  control: {
    id: string;
    name: string;
    status: string;
    remediation: string;
    evidence_links: string[];
  };
};

const fallbackControl: ControlResponse = {
  control: {
    id: "",
    name: "Unknown control",
    status: "unknown",
    remediation: "No remediation available.",
    evidence_links: [],
  },
};

export default async function ControlDetailPage({ params }: { params: { id: string } }) {
  let control = fallbackControl;

  try {
    control = await fetchUi<ControlResponse>(`/ui/controls/${params.id}`, { scopes: ["ui:controls:read"] });
  } catch {
    // fallback in non-connected environments.
  }

  return (
    <div className="space-y-6">
      <BrandHeader
        title="Control Detail"
        subtitle="Frostgate control evidence and remediation steps."
      />
      <Card>
        <CardHeader>
          <CardTitle>{control.control.name}</CardTitle>
          <CardDescription>Evidence links and remediation guidance.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Badge variant={control.control.status === "healthy" ? "default" : "outline"}>
            {control.control.status}
          </Badge>
          <p className="text-sm text-muted-foreground">{control.control.remediation}</p>
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Evidence Links</p>
            {control.control.evidence_links.length === 0 && (
              <p className="text-sm text-muted-foreground">No evidence linked.</p>
            )}
            {control.control.evidence_links.map((link) => (
              <Link key={link} href={link} className="block text-sm text-accent hover:underline">
                {link}
              </Link>
            ))}
          </div>
          <Link href="/controls" className="text-sm text-muted-foreground hover:text-foreground">
            ← Back to controls
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
