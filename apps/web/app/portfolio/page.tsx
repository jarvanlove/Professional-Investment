"use client";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Portfolio } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Wallet } from "lucide-react";
import { cn } from "@/lib/utils";

const fmt = (n: number) => n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });

export default function PortfolioPage() {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.portfolio().then(setPf).catch((e) => setError(String(e))); }, []);

  const rows = useMemo(() => {
    if (!pf) return [];
    const all = pf.funds.flatMap((f) =>
      f.lots.map((lot) => ({
        ...lot,
        code: f.code,
        name: f.name,
        nav: f.nav,
      }))
    );
    // 免费批次在前；同费率下持有天数多的在前
    return all.sort((a, b) => {
      if (a.fee_rate !== b.fee_rate) return a.fee_rate - b.fee_rate;
      return b.holding_days - a.holding_days;
    });
  }, [pf]);

  if (error) return <main className="p-8 text-destructive">加载失败：{error}</main>;
  if (!pf) return <main className="p-8">加载中…</main>;

  const totalShares = rows.reduce((s, r) => s + r.shares, 0);
  const lockedShares = rows.filter((r) => r.fee_rate > 0).reduce((s, r) => s + r.shares, 0);

  return (
    <main className="p-8 space-y-6">
      <PageHeader
        icon={Wallet}
        title="持仓与资金"
        description="卖出前先看这里：绿色可免费赎回，红色仍在费用窗口内。"
      />

      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-base">赎回费窗口总览</CardTitle>
            <div className="text-sm text-muted-foreground">
              共 {fmt(totalShares)} 份 · {lockedShares > 0 ? `${fmt(lockedShares)} 份在窗口内` : "全部免费"}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {rows.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>基金</TableHead>
                  <TableHead className="text-right">买入日期</TableHead>
                  <TableHead className="text-right">份额</TableHead>
                  <TableHead className="text-right">持有天数</TableHead>
                  <TableHead className="text-right">赎回费率</TableHead>
                  <TableHead className="text-right">状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((lot) => {
                  const free = lot.fee_rate === 0;
                  return (
                    <TableRow key={`${lot.code}-${lot.buy_date}`} className={cn(!free && "bg-buy/5")}>
                      <TableCell>
                        <div className="font-medium">{lot.name}</div>
                        <div className="text-xs text-muted-foreground">{lot.code}</div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{lot.buy_date}</TableCell>
                      <TableCell className="text-right tabular-nums">{lot.shares}</TableCell>
                      <TableCell className="text-right tabular-nums">{lot.holding_days} 天</TableCell>
                      <TableCell className={cn("text-right tabular-nums", !free && "text-buy font-medium")}>
                        {(lot.fee_rate * 100).toFixed(2)}%
                      </TableCell>
                      <TableCell className={cn("text-right text-sm", free ? "text-sell" : "text-buy font-medium")}>
                        {free ? "可免费赎回" : "费用窗口内"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">暂无持仓批次。</p>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        赎回费以销售平台实际持有天数为准；本页费率由 FIFO 批次推算，供卖出参考。
      </p>
    </main>
  );
}
