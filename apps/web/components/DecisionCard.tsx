import type { FundDecision } from "@/lib/types";
import { REASON_LABELS } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const GATE_LABELS: Record<string, string> = {
  portfolio: "组合风险闸门", score: "趋势闸门", position: "追高闸门", cash: "资金闸门",
};
const ACTION_STYLE = { BUY: "bg-green-600", SELL: "bg-red-600", HOLD: "bg-gray-400" } as const;

export function DecisionCard({ d }: { d: FundDecision }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{d.name} <span className="text-xs text-muted-foreground">{d.code}</span></CardTitle>
          <Badge className={ACTION_STYLE[d.action]}>
            {d.action === "HOLD" ? "不动" : `${d.action === "BUY" ? "买入" : "卖出"} ¥${d.amount.toLocaleString("zh-CN")}`}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="text-sm space-y-2">
        <div>趋势评分 <b>{d.score}/5</b> · 乘数 {d.score_multiplier} · 波动 {(d.vol20 * 100).toFixed(0)}% → ×{d.vol_multiplier}</div>
        <div>目标权重 {(d.target_weight * 100).toFixed(2)}%（¥{d.target_value.toFixed(0)}）· 当前 ¥{d.current_value.toFixed(0)} · 差额 ¥{d.gap.toFixed(0)}</div>
        <div className="flex gap-3">
          {Object.entries(d.gates).map(([k, ok]) => (
            <span key={k}>{ok ? "✅" : "❌"}{GATE_LABELS[k] ?? k}</span>
          ))}
        </div>
        <div>理由：<Badge variant="outline">{d.reason_code} {REASON_LABELS[d.reason_code]}</Badge></div>
        {d.notes.length > 0 && <ul className="text-amber-700 list-disc pl-5">{d.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>}
      </CardContent>
    </Card>
  );
}
