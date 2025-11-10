import { TenantShell } from "@/components/layout/tenant-shell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <TenantShell>{children}</TenantShell>;
}
