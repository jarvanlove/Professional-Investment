import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  title,
  value,
  sub,
  icon: Icon,
  tone = "default",
}: {
  title: string;
  value: string;
  sub?: string;
  icon?: React.ComponentType<{ className?: string }>;
  tone?: "default" | "warning" | "danger";
}) {
  return (
    <Card
      className={cn(
        "border-l-4",
        tone === "default" && "border-l-primary",
        tone === "warning" && "border-l-amber-500",
        tone === "danger" && "border-l-destructive"
      )}
    >
      <CardContent className="flex items-start justify-between gap-3 pt-5">
        <div className="min-w-0">
          <div className="text-sm text-muted-foreground">{title}</div>
          <div
            className={cn(
              "text-2xl font-bold tabular-nums mt-1",
              tone === "warning" && "text-amber-600",
              tone === "danger" && "text-destructive"
            )}
          >
            {value}
          </div>
          {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
        </div>
        {Icon && (
          <div
            className={cn(
              "flex size-9 shrink-0 items-center justify-center rounded-lg",
              tone === "default" && "bg-primary/8 text-primary",
              tone === "warning" && "bg-amber-500/10 text-amber-600",
              tone === "danger" && "bg-destructive/10 text-destructive"
            )}
          >
            <Icon className="size-4" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
