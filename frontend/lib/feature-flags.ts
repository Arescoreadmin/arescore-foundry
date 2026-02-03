export const features = [
  "dashboards",
  "posture",
  "forensics",
  "controls",
  "admin-console",
  "training",
  "sites",
  "devices",
  "audit-stream",
  "leaderboard",
] as const;

export type FeatureFlag = (typeof features)[number];

export type FeatureMatrix = Record<string, FeatureFlag[]>;

export const featureMatrix: FeatureMatrix = {
  core: ["dashboards", "posture", "forensics", "controls", "admin-console", "sites"],
  advanced: [
    "dashboards",
    "posture",
    "forensics",
    "controls",
    "admin-console",
    "training",
    "sites",
    "devices",
    "audit-stream",
  ],
  prime: [
    "dashboards",
    "posture",
    "forensics",
    "controls",
    "admin-console",
    "training",
    "sites",
    "devices",
    "audit-stream",
    "leaderboard",
  ],
};

export const featureDescriptions: Record<FeatureFlag, string> = {
  dashboards: "Runic telemetry dashboards with streaming overlays.",
  posture: "Security posture tiles and denial trend monitoring.",
  forensics: "Chain of custody verification with evidence exports.",
  controls: "Invariant proof matrix with remediation guidance.",
  "admin-console": "Tenant admin controls, keys, quotas, and audit logs.",
  training: "Orchestrate FrostGate training rituals and rune calibration.",
  sites: "Manage gateways, shards, and geo-segmented wards.",
  devices: "Inspect guardian devices with pulse diagnostics.",
  "audit-stream": "Trace audit glyphs in real time across the mesh.",
  leaderboard: "Track elite conductors ranked by resonance stability.",
};
