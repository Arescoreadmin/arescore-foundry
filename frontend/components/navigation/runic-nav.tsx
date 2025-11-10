"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn, frostgateGradient } from "@/lib/utils";
import { navItems } from "@/lib/navigation";
import { TenantFeatureGate } from "@/context/auth-context";

export function RunicNav() {
  const pathname = usePathname();

  return (
    <nav className="space-y-2">
      {navItems.map((item) => {
        const isActive = pathname?.startsWith(item.href);
        return (
          <TenantFeatureGate key={item.name} feature={item.feature}>
            <Link
              href={item.href}
              className={cn(
                "group relative flex items-start gap-3 rounded-xl border border-border/60 bg-background/60 p-4 transition",
                "hover:border-accent/60 hover:bg-foreground/5",
                isActive && "border-transparent bg-gradient-to-r text-primary-foreground",
                isActive && `from-primary/60 via-secondary/50 to-accent/60`
              )}
            >
              <span
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg border border-border/50 bg-background text-accent",
                  "group-hover:bg-gradient-to-br group-hover:from-primary/20 group-hover:to-secondary/20"
                )}
              >
                <item.icon className="h-5 w-5" />
              </span>
              <span>
                <p className="font-semibold text-sm">{item.name}</p>
                <p className="text-xs text-muted-foreground">{item.description}</p>
              </span>
              {isActive && (
                <span
                  aria-hidden
                  className={cn(
                    "absolute inset-y-0 right-0 w-1 rounded-r-xl bg-gradient-to-b",
                    frostgateGradient
                  )}
                />
              )}
            </Link>
          </TenantFeatureGate>
        );
      })}
    </nav>
  );
}
