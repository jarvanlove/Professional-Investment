"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PortfolioLive } from "@/lib/api";
import type { Portfolio, SignalReport } from "@/lib/types";
import { REGIME_LABELS } from "@/lib/types";
import { StatCard } from "@/components/StatCard";
import { WeightChart, type WeightPoint } from "@/components/WeightChart";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LayoutDashboard, PiggyBank, TrendingDown, Vault, Percent, Wallet, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

const fmt = (n: number) => n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
const signed = (n: number) => `${n >= 0 ? "+" : ""}${fmt(n)}`;

export default function Dashboard() {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [live, setLive] = useState<PortfolioLive | null>(null);
  const [sig, setSig] = useState<SignalReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);

  const loadPortfolio = () =>
    api.portfolio().then(setPf).catch((e) => setError(String(e)));

  const loadLive = () =>
    api.portfolioLive().then(setLive).catch(() => setLive(null));

  useEffect(() => {
    loadPortfolio();
    loadLive();
    api.latestSignals().then(setSig).catch(() => setSig(null)); // 404 容忍
  }, []);

  async function refreshNav() {
    setRefreshing(true); setRefreshMsg(null); setError(null);
    try {
      const r = await api.refreshNav();
      await loadPortfolio();
      await loadLive();
      const failed = r.results.filter((x) => x.status !== "ok");
      setRefreshMsg(failed.length
        ? `部分净值抓取失败：${failed.map((x) => x.code).join("、")}`
        : `净值已更新：${r.results.map((x) => `${x.code}+${x.added}`).join("，")}`);
    } catch (e) {
      setError(`刷新失败：${e}`);
    }
    setRefreshing(false);
  }

  async function refreshLive() {
    setRefreshing(true); setRefreshMsg(null); setError(null);
    try {
      await loadLive();
      setRefreshMsg("盘中估算已刷新");
    } catch (e) {
      setError(`刷新失败：${e}`);
    }
    setRefreshing(false);
  }

  if (error) return <main className="p-8 text-destructive">加载失败：{error}（quant-api 是否在运行？）</main>;
  if (!pf) return <main className="p-8">加载中…</main>;

  const a = pf.account;
  const latestNavDate = pf.funds.find((f) => f.nav_date)?.nav_date;

  const weights: WeightPoint[] = sig
    ? sig.decisions.map((d) => ({
        name: d.name.slice(0, 4), current: +(d.current_value / sig.total_value * 100).toFixed(1),
        target: +(d.target_weight * 100).toFixed(1),
      }))
    : pf.funds.map((f) => ({ name: f.name.slice(0, 4), current: +(f.weight * 100).toFixed(1), target: 0 }));

  const ddTone = a.portfolio_dd >= 0.12 ? "danger" : a.portfolio_dd >= 0.06 ? "warning" : "default";
  const peakTone = a.peak_profit_rate >= 0.12 ? "warning" : "default";

  const totalEstPnl = live?.total_estimated_pnl ?? 0;
  const estTone = totalEstPnl > 0 ? "danger" : totalEstPnl < 0 ? "success" : "default"; // 红涨绿跌
  const liveTime = live?.as_of;
  const hasAnyEstimate = live?.funds.some((f) => f.has_estimate) ?? false;

  return (
    <main className="p-8 space-y-6">
      <PageHeader
        icon={LayoutDashboard}
        title="仪表盘"
        description="账户总览与盘中估算。下方“实时估算”区域交易日白天可刷新。"
      />
      {refreshMsg && <p className="text-sm text-muted-foreground">{refreshMsg}</p>}

      {/* 官方快照 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="账户总资产" value={`¥${fmt(a.total_value)}`} sub={`净投入 ¥${fmt(a.net_contributed)}`} icon={PiggyBank} />
        <StatCard title="组合回撤" value={pct(a.portfolio_dd)} sub="回撤 ≥6% 停加科技，≥12% 防守" icon={TrendingDown} tone={ddTone} />
        <StatCard title="现金比例" value={pct(a.total_value ? a.cash / a.total_value : 0)} sub={`现金 ¥${fmt(a.cash)}`} icon={Vault} />
        <StatCard title="峰值利润率" value={pct(a.peak_profit_rate)} sub="≥12% 锁定一半浮盈" icon={Percent} tone={peakTone} />
      </div>

      {/* 实时估算 */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold">实时估算</span>
            {liveTime && <span className="text-sm text-muted-foreground">数据时间 {liveTime}</span>}
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={refreshLive} disabled={refreshing} variant="outline" size="sm">
              {refreshing ? <RefreshCw className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
              刷新估算
            </Button>
            <Button onClick={refreshNav} disabled={refreshing} variant="secondary" size="sm">
              刷新净值
            </Button>
          </div>
        </div>

        {!hasAnyEstimate && (
          <p className="text-sm text-muted-foreground">
            当前非交易时间或暂无盘中估算。点击“刷新估算”重试；晚上净值公布后请点“刷新净值”。
          </p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="今日盈亏（估算）"
            value={`¥${signed(totalEstPnl)}`}
            sub={liveTime ? `按 ${liveTime} 盘中估算` : "暂无盘中估算"}
            icon={Wallet}
            tone={estTone}
          />
          {live?.funds.map((f) => {
            const pnl = f.estimated_pnl ?? 0;
            const ret = f.change_pct ?? 0;
            const isUp = pnl >= 0;
            return (
              <Card key={f.code} className="flex flex-col justify-between">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground truncate" title={f.name}>{f.name}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  <div className={cn("text-2xl font-bold tabular-nums", isUp ? "text-buy" : "text-sell")}>
                    ¥{signed(pnl)}
                  </div>
                  <div className={cn("text-sm tabular-nums", isUp ? "text-buy" : "text-sell")}>
                    {f.has_estimate ? (
                      <>{ret >= 0 ? "+" : ""}{(ret * 100).toFixed(2)}% {f.note && <span className="text-muted-foreground ml-1">({f.note})</span>}</>
                    ) : (
                      <span className="text-muted-foreground">暂无估算</span>
                    )}
                  </div>
                  {f.has_estimate && f.estimated_nav && (
                    <div className="text-xs text-muted-foreground tabular-nums">
                      估 {f.estimated_nav.toFixed(4)} · 市值 ¥{fmt(f.estimated_value)}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 items-start">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">当前权重 vs 目标权重</CardTitle>
            {sig && <div className="text-sm text-muted-foreground">{REGIME_LABELS[sig.regime] ?? sig.regime}模式 · {sig.as_of}</div>}
          </CardHeader>
          <CardContent>
            <WeightChart data={weights} />
            {!sig && <p className="text-sm text-muted-foreground mt-2">尚未生成信号快照——到"每周信号"页点"计算信号"。</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">持仓明细（{latestNavDate ? `净值日期 ${latestNavDate}` : "暂无净值"}）</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>基金</TableHead>
                  <TableHead className="text-right">份额</TableHead>
                  <TableHead className="text-right">最新净值</TableHead>
                  <TableHead className="text-right">市值</TableHead>
                  <TableHead className="text-right">日涨跌</TableHead>
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
                    <TableCell className={cn("text-right tabular-nums", (f.daily_return ?? 0) > 0 ? "text-buy" : "text-sell")}>
                      {(f.daily_return ?? 0) >= 0 ? "+" : ""}{((f.daily_return ?? 0) * 100).toFixed(2)}%
                    </TableCell>
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
