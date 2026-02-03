import { Badge } from "@/components/ui/badge";

type BrandHeaderProps = {
  title: string;
  subtitle: string;
};

export function BrandHeader({ title, subtitle }: BrandHeaderProps) {
  return (
    <div className="rounded-2xl border border-border/60 bg-background/70 p-5 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-muted-foreground">Frostgate</p>
          <h2 className="text-2xl font-semibold frostgate-brand">{title}</h2>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        <Badge variant="outline" className="border-accent/40 text-accent">
          Frostgate Command
        </Badge>
      </div>
    </div>
  );
}
