import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { BrandHeader } from "@/components/layout/brand-header";
import { fetchUi } from "@/lib/ui-api";
import { ForensicsExport } from "./forensics-export";

type ChainVerifyResponse = {
  status: "PASS" | "FAIL";
  first_bad_record: string | null;
};

const fallbackVerify: ChainVerifyResponse = { status: "FAIL", first_bad_record: null };

export default async function ForensicsPage() {
  let verification = fallbackVerify;

  try {
    verification = await fetchUi<ChainVerifyResponse>("/ui/forensics/chain/verify", {
      scopes: ["ui:forensics:read"],
    });
  } catch {
    // use fallback in non-connected environments.
  }

  return (
    <div className="space-y-6">
      <BrandHeader
        title="Evidence & Forensics"
        subtitle="Frostgate chain-of-custody verification and forensic readiness."
      />
      <Card>
        <CardHeader>
          <CardTitle>Evidence &amp; Forensics</CardTitle>
          <CardDescription>Chain-of-custody verification and forensic readiness.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-xl border border-border/60 bg-background/60 p-4">
            <div>
              <p className="text-sm font-semibold">Chain Verification</p>
              <p className="text-xs text-muted-foreground">Detect tampering in audit records.</p>
            </div>
            <Badge variant={verification.status === "PASS" ? "default" : "destructive"}>
              {verification.status}
            </Badge>
          </div>
          {verification.first_bad_record && (
            <>
              <Separator />
              <p className="text-sm text-muted-foreground">
                First bad record: <span className="font-semibold text-foreground">{verification.first_bad_record}</span>
              </p>
            </>
          )}
        </CardContent>
      </Card>

      <ForensicsExport />
    </div>
  );
}
