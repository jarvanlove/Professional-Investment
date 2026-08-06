"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Portfolio } from "@/lib/types";

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
        <section key={f.code} className="border rounded p-4 space-y-2">
          <div className="flex justify-between items-center">
            <h2 className="font-semibold">{f.name} <span className="text-xs text-muted-foreground">{f.code}</span></h2>
            <div className="text-sm">
              {f.shares} 份 × {f.nav ?? "—"} = <b>¥{fmt(f.value)}</b>（{(f.weight * 100).toFixed(1)}%）
              {f.nav_date && <span className="text-muted-foreground"> · 净值日期 {f.nav_date}</span>}
            </div>
          </div>
          {f.lots.length > 0 ? (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-muted-foreground">
                <th>买入日期</th><th>份额</th><th>持有天数</th><th>当前赎回费率</th>
              </tr></thead>
              <tbody>
                {f.lots.map((lot, i) => (
                  <tr key={i} className={lot.fee_rate > 0 ? "text-red-700" : ""}>
                    <td>{lot.buy_date}</td><td>{lot.shares}</td><td>{lot.holding_days} 天</td>
                    <td>{lot.fee_rate > 0 ? `${(lot.fee_rate * 100).toFixed(2)}%（费用窗口内）` : "0（免费）"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-sm text-muted-foreground">无持仓批次</p>}
        </section>
      ))}
      <p className="text-xs text-muted-foreground">赎回费以销售平台实际持有天数为准；本页费率由 FIFO 批次推算。</p>
    </main>
  );
}
