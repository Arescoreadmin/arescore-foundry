"use client";

import { Fragment, useMemo } from "react";
import Link from "next/link";
import { ChevronDown, Radio, Sparkle, User2 } from "lucide-react";
import { RunicNav } from "@/components/navigation/runic-nav";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/context/auth-context";
import { useTelemetry } from "@/context/telemetry-context";
import { featureDescriptions, featureMatrix } from "@/lib/feature-flags";

export function TenantShell({ children }: { children: React.ReactNode }) {
  const { user, setPlan } = useAuth();
  const { frames, status, lastUpdated } = useTelemetry();

  const telemetryPreview = useMemo(() => frames.slice(0, 5), [frames]);

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <aside className="rune-grid relative w-full border-b border-border/60 bg-background/80 p-8 lg:w-80 lg:border-r lg:border-b-0">
        <div className="flex items-center justify-between">
          <Link href="/dashboard" className="font-semibold uppercase tracking-[0.28em] text-xs text-muted-foreground">
            FrostGate Foundry
          </Link>
          <Badge variant="glow" className="px-3 py-1 text-[10px] uppercase tracking-wider">
            {user.plan} plan
          </Badge>
        </div>
        <p className="mt-6 text-sm text-muted-foreground">
          Runic operations cockpit for cross-gate observatories.
        </p>
        <div className="mt-8 space-y-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Plan tier</label>
          <div className="flex gap-2">
            {(Object.keys(featureMatrix) as Array<typeof user.plan>).map((plan) => (
              <Button
                key={plan}
                variant={plan === user.plan ? "default" : "outline"}
                size="sm"
                className="capitalize"
                onClick={() => setPlan(plan)}
              >
                {plan}
              </Button>
            ))}
          </div>
        </div>
        <Separator className="my-8" />
        <RunicNav />
        <Separator className="my-8" />
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-2">
              <Radio className={`h-3 w-3 ${status === "streaming" ? "text-success animate-pulse-signal" : "text-warning"}`} />
              {status === "streaming" ? "Telemetry linked" : status === "connecting" ? "Rebinding" : "Offline"}
            </span>
            <span>{lastUpdated ? lastUpdated.toLocaleTimeString() : "--:--"}</span>
          </div>
          <div className="rounded-xl border border-border/60 bg-foreground/5 p-4">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Recent frames</p>
            <ul className="mt-3 space-y-2 text-xs">
              {telemetryPreview.map((frame) => (
                <li key={frame.id} className="flex items-center justify-between text-muted-foreground">
                  <span className="flex items-center gap-2">
                    <span className="font-mono text-sm text-foreground">{frame.glyph}</span>
                    {frame.location}
                  </span>
                  <span className="font-semibold text-foreground">{frame.resonance}%</span>
                </li>
              ))}
              {telemetryPreview.length === 0 && <li className="text-muted-foreground">Awaiting stream...</li>}
            </ul>
          </div>
        </div>
      </aside>
      <main className="flex-1 bg-background/40 p-8 lg:p-10">
        <header className="mb-10 flex flex-col gap-6 rounded-3xl border border-border/50 bg-background/60 p-6 shadow-lg lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Welcome back, {user.handle}</h1>
            <p className="text-sm text-muted-foreground">
              Orchestrate cross-gate rituals, audit anomalies, and tune the frostfield.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" className="gap-2 text-muted-foreground">
              <Sparkle className="h-4 w-4" />
              Narrate
            </Button>
            <Button className="gap-2">
              <User2 className="h-4 w-4" />
              Summon Council
            </Button>
          </div>
        </header>
        <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
          <section className="space-y-6">
            {children}
          </section>
          <aside className="space-y-6">
            <div className="rounded-2xl border border-border/50 bg-background/70 p-6">
              <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-muted-foreground">Abilities</h2>
              <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
                {featureMatrix[user.plan].map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <span className="mt-1 text-xs text-accent">◆</span>
                    <span>
                      <span className="font-medium capitalize text-foreground">{feature.replace("-", " ")}</span>
                      <p className="text-xs text-muted-foreground">{featureDescriptions[feature]}</p>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-border/50 bg-gradient-to-br from-foreground/5 via-transparent to-transparent p-6">
              <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-muted-foreground">Quick Actions</h2>
              <div className="mt-4 space-y-3">
                {["Generate glyph rune", "Open spectral window", "Queue ward recalibration"].map((action) => (
                  <Fragment key={action}>
                    <Button variant="outline" className="w-full justify-between text-sm">
                      {action}
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </Fragment>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
