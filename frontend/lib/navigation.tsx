import { BookA, Cog, MonitorSmartphone, Network, ShieldAlert, Sparkles } from "lucide-react";
import type { ComponentType } from "react";
import type { FeatureFlag } from "@/lib/feature-flags";

export type NavItem = {
  name: string;
  href: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  feature: FeatureFlag;
};

export const navItems: NavItem[] = [
  {
    name: "Dashboard",
    href: "/dashboard",
    description: "Monitor resonance, wards, and runic anomalies in one glance.",
    icon: MonitorSmartphone,
    feature: "dashboards",
  },
  {
    name: "Training",
    href: "/training",
    description: "Guide cadets through FrostGate drills and chronicle progress.",
    icon: Sparkles,
    feature: "training",
  },
  {
    name: "Sites & Segments",
    href: "/sites",
    description: "Map gate shards, environmental modifiers, and warding status.",
    icon: Network,
    feature: "sites",
  },
  {
    name: "Devices",
    href: "/devices",
    description: "Inspect guardians, calibrate conduits, and sync rune firmware.",
    icon: Cog,
    feature: "devices",
  },
  {
    name: "Audit Viewer",
    href: "/audit",
    description: "Trace audit glyphs and anomaly trails across the mesh logs.",
    icon: ShieldAlert,
    feature: "audit-stream",
  },
  {
    name: "Leaderboard",
    href: "/leaderboard",
    description: "Celebrate elite conductors ranked by resonance mastery.",
    icon: BookA,
    feature: "leaderboard",
  },
];
