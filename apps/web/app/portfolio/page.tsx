"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Portfolio } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const fmt = (n: number) => n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });

export default function PortfolioPage() {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.portfolio().then(setPf).catch((e) => setError(String(e))); }, []);

  if (error) return <main className="p-8 text-red-600">加载失败：{error}</main>;
  if (!pf) return <main className="p-8">加载中…</main>;

  return (
    <main className="p-8 space-y-6">
      <h1 className="text-xl font-bold">持仓与资金</h1>
      <p className="text-sm text-muted-foreground">
        现金 ¥{fmt(pf.account.cash)} · 净投入 ¥{fmt(pf.account.net_contributed)} · 总资产 ¥{fmt(pf.account.total_value)}
      </p>
      {pf.funds.map((f) => (
        <Card key={f.code}>
          <CardHeader className="pb-2">
            <div className="flex justify-between items-center">
              <CardTitle className="text-base">{f.name} <span className="text-xs text-muted-foreground">{f.code}</span></CardTitle>
              <div className="text-sm">
                {f.shares} 份 × {f.nav ?? "—"} = <b>¥{fmt(f.value)}</b>（{(f.weight * 100).toFixed(1)}%）
                {f.nav_date && <span className="text-muted-foreground"> · 净值日期 {f.nav_date}</span>}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {f.lots.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>买入日期</TableHead><TableHead>份额</TableHead>
                    <TableHead>持有天数</TableHead><TableHead>当前赎回费率</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {f.lots.map((lot, i) => (
                    <TableRow key={i} className={lot.fee_rate > 0 ? "text-red-700" : ""}>
                      <TableCell>{lot.buy_date}</TableCell>
                      <TableCell>{lot.shares}</TableCell>
                      <TableCell>{lot.holding_days} 天</TableCell>
                      <TableCell>{lot.fee_rate > 0 ? `${(lot.fee_rate * 100).toFixed(2)}%（费用窗口内）` : "0（免费）"}</TableCell>
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
