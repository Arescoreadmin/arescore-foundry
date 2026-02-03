import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { fetchAdmin } from "@/lib/admin-api";
import { AdminActions } from "./admin-actions";

type TenantConsole = {
  keys: Array<{ id: string; status: string; last_rotated: string }>;
  usage: { sessions: number; quota: string };
};

type GlobalConsole = {
  tenant_count: number;
  regions: string[];
};

type AuditLog = {
  items: Array<{ event_id: string; action: string; actor: string; created_at: string }>;
};

const fallbackTenant: TenantConsole = { keys: [], usage: { sessions: 0, quota: "0%" } };
const fallbackGlobal: GlobalConsole = { tenant_count: 0, regions: [] };
const fallbackAudit: AuditLog = { items: [] };

export default async function AdminPage() {
  let tenantConsole = fallbackTenant;
  let globalConsole = fallbackGlobal;
  let auditLog = fallbackAudit;

  try {
    tenantConsole = await fetchAdmin<TenantConsole>("/admin/console/tenant", { scopes: ["admin:tenant"] });
    globalConsole = await fetchAdmin<GlobalConsole>("/admin/console/global", { scopes: ["admin:global"] });
    auditLog = await fetchAdmin<AuditLog>("/admin/console/audit-log?limit=5", { scopes: ["admin:audit:read"] });
  } catch {
    // fallback in non-connected environments.
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Admin Console</CardTitle>
          <CardDescription>Tenant and global admin visibility with audit trails.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-3 rounded-xl border border-border/60 bg-background/60 p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Tenant overview</p>
            <div className="flex items-center justify-between text-sm">
              <span>Active keys</span>
              <Badge variant="outline">{tenantConsole.keys.length}</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span>Sessions</span>
              <Badge variant="outline">{tenantConsole.usage.sessions}</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span>Quota usage</span>
              <Badge variant="outline">{tenantConsole.usage.quota}</Badge>
            </div>
          </div>
          <div className="space-y-3 rounded-xl border border-border/60 bg-background/60 p-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Global oversight</p>
            <div className="flex items-center justify-between text-sm">
              <span>Tenants</span>
              <Badge variant="outline">{globalConsole.tenant_count}</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span>Regions</span>
              <Badge variant="outline">{globalConsole.regions.join(", ") || "none"}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <AdminActions />

      <Card>
        <CardHeader>
          <CardTitle>Audit Log</CardTitle>
          <CardDescription>Recent admin events for this tenant.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {auditLog.items.length === 0 && <p className="text-sm text-muted-foreground">No audit events yet.</p>}
          {auditLog.items.map((event) => (
            <div key={event.event_id} className="rounded-xl border border-border/60 bg-background/60 p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold">{event.action}</span>
                <Badge variant="outline">{event.actor}</Badge>
              </div>
              <Separator className="my-2" />
              <p className="text-xs text-muted-foreground">{event.created_at}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
