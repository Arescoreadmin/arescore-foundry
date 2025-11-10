import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/layout/theme-provider";
import { AuthProvider } from "@/context/auth-context";
import { TelemetryProvider } from "@/context/telemetry-context";

export const metadata: Metadata = {
  title: "FrostGate Foundry",
  description: "Plan-aware FrostGate cockpit with runic navigation and live telemetry.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <AuthProvider>
            <TelemetryProvider>{children}</TelemetryProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
