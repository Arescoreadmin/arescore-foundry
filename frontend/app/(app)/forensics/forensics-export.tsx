"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type ExportResponse = {
  token: string;
  path: string;
};

const UI_API_BASE = process.env.NEXT_PUBLIC_UI_API_BASE ?? "http://localhost:8090";
const DEFAULT_TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "11111111-1111-1111-1111-111111111111";

export function ForensicsExport() {
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [result, setResult] = useState<ExportResponse | null>(null);

  async function handleExport() {
    setStatus("loading");
    setResult(null);

    try {
      const response = await fetch(`${UI_API_BASE}/ui/audit/packet`, {
        method: "POST",
        headers: {
          "X-Tenant-ID": DEFAULT_TENANT_ID,
          "X-Scopes": "ui:audit:export",
          "X-Subject": "ui-demo",
          "X-Request-ID": "ui-demo-export",
        },
      });

      if (!response.ok) {
        throw new Error("Export failed");
      }

      const payload = (await response.json()) as ExportResponse;
      setResult({ token: payload.token, path: payload.path });
      setStatus("done");
    } catch {
      setStatus("error");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit Packet Export</CardTitle>
        <CardDescription>Bundle evidence, chain verification, and manifest hashes.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button onClick={handleExport} disabled={status === "loading"}>
          {status === "loading" ? "Building packet..." : "Export audit packet"}
        </Button>
        {status === "error" && <p className="text-sm text-destructive">Unable to export audit packet.</p>}
        {result && (
          <div className="rounded-xl border border-border/60 bg-background/60 p-3 text-xs text-muted-foreground">
            <p>
              <span className="font-semibold text-foreground">Token:</span> {result.token}
            </p>
            <p>
              <span className="font-semibold text-foreground">Path:</span> {result.path}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
