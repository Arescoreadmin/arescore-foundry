"use client";

import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { featureMatrix, type FeatureFlag } from "@/lib/feature-flags";

export type PlanTier = "core" | "advanced" | "prime";

export type TenantUser = {
  id: string;
  handle: string;
  runeColor: string;
  plan: PlanTier;
  abilities: FeatureFlag[];
};

type AuthContextValue = {
  user: TenantUser;
  setPlan: (plan: PlanTier) => void;
  hasFeature: (feature: FeatureFlag) => boolean;
};

const defaultUser: TenantUser = {
  id: "tenant-demo-01",
  handle: "magi@frostgate",
  runeColor: "from-primary to-secondary",
  plan: "advanced",
  abilities: featureMatrix["advanced"],
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState(defaultUser);

  const value = useMemo<AuthContextValue>(() => {
    const matrix = featureMatrix[user.plan];

    return {
      user,
      setPlan: (plan) =>
        setUser((prev) => ({
          ...prev,
          plan,
          abilities: featureMatrix[plan],
        })),
      hasFeature: (feature) => matrix.includes(feature),
    };
  }, [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return ctx;
}

export function TenantFeatureGate({
  feature,
  children,
  fallback = null,
}: {
  feature: FeatureFlag;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { hasFeature } = useAuth();

  if (!hasFeature(feature)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
