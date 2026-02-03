"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const ADMIN_API_BASE = process.env.NEXT_PUBLIC_ADMIN_API_BASE ?? "http://localhost:8091";
const DEFAULT_TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "11111111-1111-1111-1111-111111111111";

export function AdminActions() {
  const [message, setMessage] = useState<string | null>(null);

  async function rotateKeys() {
    setMessage(null);
    const response = await fetch(`${ADMIN_API_BASE}/admin/console/keys/rotate`, {
      method: "POST",
      headers: {
        "X-Tenant-ID": DEFAULT_TENANT_ID,
        "X-Scopes": "admin:keys:write admin:tenant",
        "X-Subject": "admin-demo",
        "X-Request-ID": "admin-rotate",
        "X-CSRF-Token": "admin-demo-csrf",
      },
    });
    setMessage(response.ok ? "Keys rotated and audit event recorded." : "Failed to rotate keys.");
  }

  async function updateQuota() {
    setMessage(null);
    const response = await fetch(`${ADMIN_API_BASE}/admin/console/tenants/${DEFAULT_TENANT_ID}/quota`, {
      method: "POST",
      headers: {
        "X-Scopes": "admin:global admin:quota:write",
        "X-Subject": "admin-demo",
        "X-Request-ID": "admin-quota",
        "X-CSRF-Token": "admin-demo-csrf",
      },
    });
    setMessage(response.ok ? "Quota updated and audit event recorded." : "Failed to update quota.");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Admin Actions</CardTitle>
        <CardDescription>State-changing actions recorded with structured audit events.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-3">
          <Button onClick={rotateKeys}>Rotate keys</Button>
          <Button variant="outline" onClick={updateQuota}>
            Update quota
          </Button>
        </div>
        {message && <p className="text-sm text-muted-foreground">{message}</p>}
      </CardContent>
    </Card>
  );
}
