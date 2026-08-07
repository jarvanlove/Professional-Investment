"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Portfolio } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Wallet, Vault, PiggyBank, Landmark } from "lucide-react";
import { cn } from "@/lib/utils";

const fmt = (n: number) => n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });

export default function PortfolioPage() {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.portfolio().then(setPf).catch((e) => setError(String(e))); }, []);

  if (error) return <main className="p-8 text-destructive">加载失败：{error}</main>;
  if (!pf) return <main className="p-8">加载中…</main>;

  return (
    <main className="p-8 space-y-6">
      <PageHeader icon={Wallet} title="持仓与资金" description="按 FIFO 批次推算的赎回费窗口与各基金权重。" />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard title="现金" value={`¥${fmt(pf.account.cash)}`} icon={Vault} />
        <StatCard title="净投入" value={`¥${fmt(pf.account.net_contributed)}`} icon={PiggyBank} />
        <StatCard title="总资产" value={`¥${fmt(pf.account.total_value)}`} icon={Landmark} />
      </div>

      {pf.funds.map((f) => (
        <Card key={f.code}>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap justify-between items-center gap-2">
              <CardTitle className="text-base">
                {f.name} <span className="text-xs text-muted-foreground font-normal">{f.code}</span>
              </CardTitle>
              <div className="text-sm tabular-nums">
                {f.shares} 份 × {f.nav ?? "—"} = <b className="text-base">¥{fmt(f.value)}</b>
                {f.nav_date && <span className="text-muted-foreground"> · 净值日期 {f.nav_date}</span>}
              </div>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(f.weight * 100, 100)}%` }} />
              </div>
              <span className="text-xs text-muted-foreground tabular-nums shrink-0">{(f.weight * 100).toFixed(1)}%</span>
            </div>
          </CardHeader>
          <CardContent>
            {f.lots.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>买入日期</TableHead>
                    <TableHead className="text-right">份额</TableHead>
                    <TableHead className="text-right">持有天数</TableHead>
                    <TableHead className="text-right">当前赎回费率</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {f.lots.map((lot, i) => (
                    <TableRow key={i} className={cn(lot.fee_rate > 0 && "bg-buy/5")}>
                      <TableCell className="tabular-nums">{lot.buy_date}</TableCell>
                      <TableCell className="text-right tabular-nums">{lot.shares}</TableCell>
                      <TableCell className="text-right tabular-nums">{lot.holding_days} 天</TableCell>
                      <TableCell className={cn("text-right tabular-nums", lot.fee_rate > 0 && "text-buy font-medium")}>
                        {lot.fee_rate > 0 ? `${(lot.fee_rate * 100).toFixed(2)}%（费用窗口内）` : "0（免费）"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : <p className="text-sm text-muted-foreground">无持仓批次</p>}
          </CardContent>
        </Card>
      ))}
      <p className="text-xs text-muted-foreground">赎回费以销售平台实际持有天数为准；本页费率由 FIFO 批次推算。</p>
    </main>
  );
}
