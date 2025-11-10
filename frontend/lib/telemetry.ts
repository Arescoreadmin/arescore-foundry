const runes = ["ᚠ", "ᚱ", "ᛟ", "ᚨ", "ᛞ", "ᚺ", "ᛋ", "ᛇ"];
const locations = ["Helsreach", "Vost Gate", "Icelock", "Starwell", "Veilstep", "Frostmere"];

export type TelemetryFrame = {
  id: string;
  stream: "sse" | "ws" | "mock";
  glyph: string;
  resonance: number;
  stability: number;
  location: string;
  timestamp: string;
};

function makeId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `mock-${Math.random().toString(16).slice(2, 10)}`;
}

export function buildMockTelemetry(): TelemetryFrame {
  return {
    id: makeId(),
    stream: "mock",
    glyph: runes[Math.floor(Math.random() * runes.length)],
    resonance: Number((70 + Math.random() * 28).toFixed(2)),
    stability: Number((60 + Math.random() * 35).toFixed(2)),
    location: locations[Math.floor(Math.random() * locations.length)],
    timestamp: new Date().toISOString(),
  };
}
