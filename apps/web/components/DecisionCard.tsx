"use client";
import { useState } from "react";
import type { FundDecision } from "@/lib/types";
import { REASON_LABELS } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, X, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

const GATE_LABELS: Record<string, string> = {
  portfolio: "组合风险",
  score: "趋势",
  position: "追高",
  cash: "资金",
};

const ACTION_STYLE = {
  BUY: "bg-buy text-buy-foreground",
  SELL: "bg-sell text-sell-foreground",
  HOLD: "bg-muted text-muted-foreground",
} as const;

const ACTION_TEXT = { BUY: "买入", SELL: "卖出", HOLD: "不动" } as const;

const CONFIDENCE_STYLE = {
  high: "border-sell/30 bg-sell/8 text-sell",
  medium: "border-amber-500/30 bg-amber-500/10 text-amber-700",
  low: "border-buy/30 bg-buy/8 text-buy",
} as const;

const CONFIDENCE_TEXT = { high: "高置信", medium: "中置信", low: "低置信" } as const;

function Metric({ label, value, tone }: { label: string; value: string; tone?: "buy" | "sell" | "neutral" }) {
  return (
    <div className="rounded-md border bg-surface/50 p-2">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      <div className={cn("text-sm font-semibold tabular-nums", tone === "buy" && "text-buy", tone === "sell" && "text-sell")}>
        {value}
      </div>
    </div>
  );
}

export function DecisionCard({ d }: { d: FundDecision }) {
  const [open, setOpen] = useState(false);
  const actionText = ACTION_TEXT[d.action];
  const confidence = d.confidence_level ?? "high";
  const isSell = d.action === "SELL";
  const isBuy = d.action === "BUY";

  return (
    <Card className={cn(
      "h-full flex flex-col border-t-4",
      d.action === "BUY" && "border-t-buy",
      d.action === "SELL" && "border-t-sell",
      d.action === "HOLD" && "border-t-border"
    )}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base leading-tight">{d.name}</CardTitle>
            <div className="text-xs text-muted-foreground font-mono mt-0.5">{d.code}</div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <Badge className={cn("tabular-nums", ACTION_STYLE[d.action])}>
              {actionText}{isBuy || isSell ? ` ¥${d.amount.toLocaleString("zh-CN")}` : ""}
            </Badge>
            <Badge variant="outline" className={cn("text-[10px]", CONFIDENCE_STYLE[confidence])}>
              {CONFIDENCE_TEXT[confidence]}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 text-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{d.reason_code} {REASON_LABELS[d.reason_code] ?? ""}</Badge>
            {d.is_dca && <Badge variant="outline" className="text-[10px]">定投</Badge>}
          </div>
          <Button variant="ghost" size="sm" onClick={() => setOpen((v) => !v)} className="h-7 px-2">
            {open ? <ChevronUp className="size-4 mr-1" /> : <ChevronDown className="size-4 mr-1" />}
            {open ? "收起" : "详情"}
          </Button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Metric label="当前市值" value={`¥${d.current_value.toFixed(0)}`} />
          <Metric label="目标市值" value={`¥${d.target_value.toFixed(0)}`} />
          <Metric label="差额" value={`¥${d.gap.toFixed(0)}`} tone={d.gap > 0 ? "buy" : d.gap < 0 ? "sell" : "neutral"} />
          <Metric label="目标权重" value={`${(d.target_weight * 100).toFixed(2)}%`} />
          {d.base_weight != null && d.base_weight > 0 && (
            <Metric label="底仓权重" value={`${(d.base_weight * 100).toFixed(1)}%`} />
          )}
          {d.dca_upcoming != null && d.dca_upcoming > 0 && (
            <Metric label="14 天定投" value={`¥${d.dca_upcoming.toFixed(0)}`} />
          )}
          {isSell && d.est_fee != null && d.est_fee > 0 && (
            <Metric label="预估赎回费" value={`¥${d.est_fee.toFixed(2)}`} tone="sell" />
          )}
          {isSell && d.net_amount != null && d.net_amount > 0 && (
            <Metric label="实收金额" value={`¥${d.net_amount.toFixed(2)}`} />
          )}
        </div>

        {open && (
          <div className="space-y-2.5 pt-1 border-t">
            <div className="text-xs text-muted-foreground tabular-nums">
              趋势评分 <b>{d.score}/5</b> · 乘数 {d.score_multiplier} · 波动 {(d.vol20 * 100).toFixed(0)}% → ×{d.vol_multiplier}
            </div>
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
          </div>
        )}

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
