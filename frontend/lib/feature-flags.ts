export const features = [
  "dashboards",
  "training",
  "sites",
  "devices",
  "audit-stream",
  "leaderboard",
] as const;

export type FeatureFlag = (typeof features)[number];

export type FeatureMatrix = Record<string, FeatureFlag[]>;

export const featureMatrix: FeatureMatrix = {
  core: ["dashboards", "sites"],
  advanced: ["dashboards", "training", "sites", "devices", "audit-stream"],
  prime: ["dashboards", "training", "sites", "devices", "audit-stream", "leaderboard"],
};

export const featureDescriptions: Record<FeatureFlag, string> = {
  dashboards: "Runic telemetry dashboards with streaming overlays.",
  training: "Orchestrate FrostGate training rituals and rune calibration.",
  sites: "Manage gateways, shards, and geo-segmented wards.",
  devices: "Inspect guardian devices with pulse diagnostics.",
  "audit-stream": "Trace audit glyphs in real time across the mesh.",
  leaderboard: "Track elite conductors ranked by resonance stability.",
};
