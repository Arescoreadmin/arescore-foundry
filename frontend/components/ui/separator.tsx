import * as React from "react";
import { cn } from "@/lib/utils";

export interface SeparatorProps extends React.HTMLAttributes<HTMLDivElement> {
  decorative?: boolean;
}

export const Separator = React.forwardRef<HTMLDivElement, SeparatorProps>(
  ({ className, decorative = true, role = decorative ? "presentation" : "separator", ...props }, ref) => (
    <div
      ref={ref}
      role={role}
      className={cn("h-px w-full bg-gradient-to-r from-transparent via-foreground/30 to-transparent", className)}
      {...props}
    />
  )
);
Separator.displayName = "Separator";
