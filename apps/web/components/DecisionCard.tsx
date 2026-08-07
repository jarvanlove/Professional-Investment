import type { FundDecision } from "@/lib/types";
import { REASON_LABELS } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, X, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

const GATE_LABELS: Record<string, string> = {
  portfolio: "组合风险闸门", score: "趋势闸门", position: "追高闸门", cash: "资金闸门",
};
const ACTION_STYLE = { BUY: "bg-buy text-buy-foreground", SELL: "bg-sell text-sell-foreground", HOLD: "bg-muted text-muted-foreground" } as const;

export function DecisionCard({ d }: { d: FundDecision }) {
  return (
    <Card className={cn(
      "border-t-4",
      d.action === "BUY" && "border-t-buy",
      d.action === "SELL" && "border-t-sell",
      d.action === "HOLD" && "border-t-border"
    )}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">{d.name} <span className="text-xs text-muted-foreground font-normal">{d.code}</span></CardTitle>
          <Badge className={cn("tabular-nums", ACTION_STYLE[d.action])}>
            {d.action === "HOLD" ? "不动" : `${d.action === "BUY" ? "买入" : "卖出"} ¥${d.amount.toLocaleString("zh-CN")}`}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="text-sm space-y-2.5">
        <div className="tabular-nums">趋势评分 <b>{d.score}/5</b> · 乘数 {d.score_multiplier} · 波动 {(d.vol20 * 100).toFixed(0)}% → ×{d.vol_multiplier}</div>
        <div className="tabular-nums">目标权重 {(d.target_weight * 100).toFixed(2)}%（¥{d.target_value.toFixed(0)}）· 当前 ¥{d.current_value.toFixed(0)} · 差额 ¥{d.gap.toFixed(0)}</div>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(d.gates).map(([k, ok]) => (
            <span
              key={k}
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs",
                ok
                  ? "border-sell/30 bg-sell/8 text-sell"
                  : "border-buy/30 bg-buy/8 text-buy"
              )}
            >
              {ok ? <Check className="size-3" /> : <X className="size-3" />}
              {GATE_LABELS[k] ?? k}{ok ? "·通过" : "·拦截"}
            </span>
          ))}
        </div>
        <div>理由：<Badge variant="outline">{d.reason_code} {REASON_LABELS[d.reason_code] ?? ""}</Badge></div>
        {d.notes.length > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800">
            <div className="flex items-center gap-1.5 text-xs font-medium mb-1">
              <AlertTriangle className="size-3.5" /> 注意
            </div>
            <ul className="list-disc pl-4 space-y-0.5 text-xs">
              {d.notes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
