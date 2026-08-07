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
  portfolio: "组合风险闸门", score: "趋势闸门", position: "追高闸门", cash: "资金闸门",
};
const ACTION_STYLE = { BUY: "bg-buy text-buy-foreground", SELL: "bg-sell text-sell-foreground", HOLD: "bg-muted text-muted-foreground" } as const;
const ACTION_TEXT = { BUY: "买入", SELL: "卖出", HOLD: "不动" } as const;
const CONFIDENCE_STYLE = {
  high: "border-sell/30 bg-sell/8 text-sell",
  medium: "border-amber-500/30 bg-amber-500/10 text-amber-700",
  low: "border-buy/30 bg-buy/8 text-buy",
} as const;
const CONFIDENCE_TEXT = { high: "高置信", medium: "中置信", low: "低置信" } as const;

export function DecisionCard({ d }: { d: FundDecision }) {
  const [open, setOpen] = useState(false);
  const actionText = ACTION_TEXT[d.action];
  const amountText = d.action === "HOLD" ? "" : ` ¥${d.amount.toLocaleString("zh-CN")}`;
  const confidence = d.confidence_level ?? "high";

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
          <div className="flex items-center gap-1.5">
            {d.is_dca && <Badge variant="outline" className="text-xs">定投</Badge>}
            <Badge className={cn("tabular-nums", ACTION_STYLE[d.action])}>
              {actionText}{amountText}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="text-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <span>理由：</span>
            <Badge variant="outline">{d.reason_code} {REASON_LABELS[d.reason_code] ?? ""}</Badge>
            <Badge variant="outline" className={cn(CONFIDENCE_STYLE[confidence])}>
              {CONFIDENCE_TEXT[confidence]}
            </Badge>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setOpen((v) => !v)} className="h-7 px-2">
            {open ? <ChevronUp className="size-4 mr-1" /> : <ChevronDown className="size-4 mr-1" />}
            {open ? "收起" : "详情"}
          </Button>
        </div>

        {!open && (
          <div className="text-xs text-muted-foreground tabular-nums space-y-1">
            <div>当前 ¥{d.current_value.toFixed(0)} · 目标 ¥{d.target_value.toFixed(0)} · 差额 ¥{d.gap.toFixed(0)}</div>
            {d.action === "SELL" && d.net_amount != null && d.est_fee != null && d.est_fee > 0 && (
              <div className="text-sell">
                预估赎回费 ¥{d.est_fee.toFixed(2)} · 实收 ¥{d.net_amount.toFixed(2)}
              </div>
            )}
          </div>
        )}

        {open && (
          <div className="space-y-2.5 pt-1">
            <div className="tabular-nums">趋势评分 <b>{d.score}/5</b> · 乘数 {d.score_multiplier} · 波动 {(d.vol20 * 100).toFixed(0)}% → ×{d.vol_multiplier}</div>
            <div className="tabular-nums">目标权重 {(d.target_weight * 100).toFixed(2)}%（¥{d.target_value.toFixed(0)}）· 当前 ¥{d.current_value.toFixed(0)} · 差额 ¥{d.gap.toFixed(0)}</div>
            {d.base_weight != null && d.base_weight > 0 && (
              <div className="tabular-nums text-muted-foreground">底仓权重 {(d.base_weight * 100).toFixed(2)}%</div>
            )}
            {d.dca_upcoming != null && d.dca_upcoming > 0 && (
              <div className="tabular-nums text-muted-foreground">未来 14 天定投 ¥{d.dca_upcoming.toFixed(0)}</div>
            )}
            {d.action === "SELL" && d.avg_fee_rate != null && d.avg_fee_rate > 0 && (
              <div className="tabular-nums text-sell">
                预估赎回费 ¥{(d.est_fee ?? 0).toFixed(2)}（{(d.avg_fee_rate * 100).toFixed(2)}%）· 实收 ¥{(d.net_amount ?? d.amount).toFixed(2)}
              </div>
            )}
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
