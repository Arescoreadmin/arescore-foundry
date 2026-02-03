import { BookA, Cog, MonitorSmartphone, Network, ShieldAlert, Sparkles } from "lucide-react";
import type { ComponentType } from "react";
import type { FeatureFlag } from "@/lib/feature-flags";

export type NavItem = {
  name: string;
  href: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  feature: FeatureFlag;
  scope: string;
};

export const navItems: NavItem[] = [
  {
    name: "Dashboard",
    href: "/dashboard",
    description: "Monitor resonance, wards, and runic anomalies in one glance.",
    icon: MonitorSmartphone,
    feature: "dashboards",
    scope: "ui:posture:read",
  },
  {
    name: "Security Posture",
    href: "/posture",
    description: "Track tenant posture tiles, trends, and denial drivers.",
    icon: ShieldAlert,
    feature: "posture",
    scope: "ui:posture:read",
  },
  {
    name: "Evidence & Forensics",
    href: "/forensics",
    description: "Verify chain-of-custody and export audit packets.",
    icon: Sparkles,
    feature: "forensics",
    scope: "ui:forensics:read",
  },
  {
    name: "Controls Matrix",
    href: "/controls",
    description: "Map invariants to evidence and remediation steps.",
    icon: Cog,
    feature: "controls",
    scope: "ui:controls:read",
  },
  {
    name: "Admin Console",
    href: "/admin",
    description: "Keys, quotas, and audit events for administrators.",
    icon: BookA,
    feature: "admin-console",
    scope: "admin:tenant",
  },
  {
    name: "Training",
    href: "/training",
    description: "Guide cadets through FrostGate drills and chronicle progress.",
    icon: Sparkles,
    feature: "training",
    scope: "ui:training:read",
  },
  {
    name: "Sites & Segments",
    href: "/sites",
    description: "Map gate shards, environmental modifiers, and warding status.",
    icon: Network,
    feature: "sites",
    scope: "ui:sites:read",
  },
  {
    name: "Devices",
    href: "/devices",
    description: "Inspect guardians, calibrate conduits, and sync rune firmware.",
    icon: Cog,
    feature: "devices",
    scope: "ui:devices:read",
  },
  {
    name: "Audit Viewer",
    href: "/audit",
    description: "Trace audit glyphs and anomaly trails across the mesh logs.",
    icon: ShieldAlert,
    feature: "audit-stream",
    scope: "ui:audit:read",
  },
  {
    name: "Leaderboard",
    href: "/leaderboard",
    description: "Celebrate elite conductors ranked by resonance mastery.",
    icon: BookA,
    feature: "leaderboard",
    scope: "ui:leaderboard:read",
  },
];
