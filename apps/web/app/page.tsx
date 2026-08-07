"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Portfolio, SignalReport } from "@/lib/types";
import { REGIME_LABELS } from "@/lib/types";
import { StatCard } from "@/components/StatCard";
import { WeightChart, type WeightPoint } from "@/components/WeightChart";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LayoutDashboard, PiggyBank, TrendingDown, Vault, Percent } from "lucide-react";

const fmt = (n: number) => n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

export default function Dashboard() {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [sig, setSig] = useState<SignalReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.portfolio().then(setPf).catch((e) => setError(String(e)));
    api.latestSignals().then(setSig).catch(() => setSig(null)); // 404 容忍
  }, []);

  if (error) return <main className="p-8 text-destructive">加载失败：{error}（quant-api 是否在运行？）</main>;
  if (!pf) return <main className="p-8">加载中…</main>;

  const a = pf.account;
  const weights: WeightPoint[] = sig
    ? sig.decisions.map((d) => ({
        name: d.name.slice(0, 4), current: +(d.current_value / sig.total_value * 100).toFixed(1),
        target: +(d.target_weight * 100).toFixed(1),
      }))
    : pf.funds.map((f) => ({ name: f.name.slice(0, 4), current: +(f.weight * 100).toFixed(1), target: 0 }));

  const ddTone = a.portfolio_dd >= 0.12 ? "danger" : a.portfolio_dd >= 0.06 ? "warning" : "default";
  const peakTone = a.peak_profit_rate >= 0.12 ? "warning" : "default";

  return (
    <main className="p-8 space-y-6">
      <PageHeader
        icon={LayoutDashboard}
        title="仪表盘"
        description="账户总览与权重偏离一览。"
        actions={sig && <Badge>{REGIME_LABELS[sig.regime] ?? sig.regime}模式 · {sig.as_of}</Badge>}
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="账户总资产" value={`¥${fmt(a.total_value)}`} sub={`净投入 ¥${fmt(a.net_contributed)}`} icon={PiggyBank} />
        <StatCard title="组合回撤" value={pct(a.portfolio_dd)} sub="回撤 ≥6% 停加科技，≥12% 防守" icon={TrendingDown} tone={ddTone} />
        <StatCard title="现金比例" value={pct(a.total_value ? a.cash / a.total_value : 0)} sub={`现金 ¥${fmt(a.cash)}`} icon={Vault} />
        <StatCard title="峰值利润率" value={pct(a.peak_profit_rate)} sub="≥12% 锁定一半浮盈" icon={Percent} tone={peakTone} />
      </div>
      <div className="grid lg:grid-cols-2 gap-4 items-start">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">当前权重 vs 目标权重</CardTitle>
          </CardHeader>
          <CardContent>
            <WeightChart data={weights} />
            {!sig && <p className="text-sm text-muted-foreground mt-2">尚未生成信号快照——到"每周信号"页点"计算信号"。</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">持仓明细</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>基金</TableHead>
                  <TableHead className="text-right">份额</TableHead>
                  <TableHead className="text-right">最新净值</TableHead>
                  <TableHead className="text-right">市值</TableHead>
                  <TableHead className="text-right">权重</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pf.funds.map((f) => (
                  <TableRow key={f.code}>
                    <TableCell>
                      <div className="font-medium">{f.name}</div>
                      <div className="text-xs text-muted-foreground">{f.code}</div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{f.shares}</TableCell>
                    <TableCell className="text-right tabular-nums">{f.nav ?? "—"}</TableCell>
                    <TableCell className="text-right tabular-nums font-medium">¥{fmt(f.value)}</TableCell>
                    <TableCell className="text-right tabular-nums">{pct(f.weight)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
