"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Portfolio, SignalReport } from "@/lib/types";
import { REGIME_LABELS } from "@/lib/types";
import { StatCard } from "@/components/StatCard";
import { WeightChart, type WeightPoint } from "@/components/WeightChart";
import { Badge } from "@/components/ui/badge";

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

  if (error) return <main className="p-8 text-red-600">加载失败：{error}（quant-api 是否在运行？）</main>;
  if (!pf) return <main className="p-8">加载中…</main>;

  const a = pf.account;
  const weights: WeightPoint[] = sig
    ? sig.decisions.map((d) => ({
        name: d.name.slice(0, 4), current: +(d.current_value / sig.total_value * 100).toFixed(1),
        target: +(d.target_weight * 100).toFixed(1),
      }))
    : pf.funds.map((f) => ({ name: f.name.slice(0, 4), current: +(f.weight * 100).toFixed(1), target: 0 }));

  return (
    <main className="p-8 space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">仪表盘</h1>
        {sig && <Badge>{REGIME_LABELS[sig.regime] ?? sig.regime}模式 · {sig.as_of}</Badge>}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="账户总资产" value={`¥${fmt(a.total_value)}`} sub={`净投入 ¥${fmt(a.net_contributed)}`} />
        <StatCard title="组合回撤" value={pct(a.portfolio_dd)} sub="回撤 ≥6% 停加科技，≥12% 防守" />
        <StatCard title="现金比例" value={pct(a.total_value ? a.cash / a.total_value : 0)} sub={`现金 ¥${fmt(a.cash)}`} />
        <StatCard title="峰值利润率" value={pct(a.peak_profit_rate)} sub="≥12% 锁定一半浮盈" />
      </div>
      <section>
        <h2 className="font-semibold mb-2">当前权重 vs 目标权重</h2>
        <WeightChart data={weights} />
        {!sig && <p className="text-sm text-muted-foreground">尚未生成信号快照——到"每周信号"页点"计算信号"。</p>}
      </section>
    </main>
  );
}
