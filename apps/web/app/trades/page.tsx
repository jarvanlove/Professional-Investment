"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Trade } from "@/lib/types";
import { REASON_LABELS } from "@/lib/types";
import { Button } from "@/components/ui/button";

const FUNDS: [string, string][] = [
  ["001480", "财通成长优选混合A"], ["025343", "长盛上证科创板芯片指数C"],
  ["027521", "广发科创芯片设计ETF联接C"], ["005052", "摩根标普港股通低波红利指数C"],
];
const DIRECTION_LABELS: Record<string, string> = { buy: "买入", sell: "卖出", deposit: "入金", withdraw: "出金" };

const empty = {
  date: new Date().toISOString().slice(0, 10), direction: "buy", fund_code: "001480",
  amount: "", shares: "", nav: "", reason_code: "B1", fee_estimate: "", note: "",
};

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [form, setForm] = useState(empty);
  const [error, setError] = useState<string | null>(null);
  const isFundTrade = form.direction === "buy" || form.direction === "sell";

  const load = () => api.trades().then(setTrades).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    try {
      await api.createTrade({
        date: form.date,
        direction: form.direction as Trade["direction"],
        fund_code: isFundTrade ? form.fund_code : null,
        amount: parseFloat(form.amount),
        shares: isFundTrade ? parseFloat(form.shares) : null,
        nav: isFundTrade ? parseFloat(form.nav) : null,
        reason_code: isFundTrade ? form.reason_code : null,
        fee_estimate: form.fee_estimate ? parseFloat(form.fee_estimate) : null,
        note: form.note || null,
      });
      setForm(empty);
      load();
    } catch (err) { setError(String(err)); }
  }

  const input = "border rounded px-2 py-1 text-sm";
  return (
    <main className="p-8 space-y-6">
      <h1 className="text-xl font-bold">交易日志</h1>
      <form onSubmit={submit} className="flex flex-wrap gap-2 items-end border rounded p-4">
        <label className="text-sm">日期<input type="date" className={input} value={form.date}
          onChange={(e) => setForm({ ...form, date: e.target.value })} /></label>
        <label className="text-sm">方向
          <select className={input} value={form.direction}
            onChange={(e) => setForm({ ...form, direction: e.target.value })}>
            {Object.entries(DIRECTION_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select></label>
        {isFundTrade && <>
          <label className="text-sm">基金
            <select className={input} value={form.fund_code}
              onChange={(e) => setForm({ ...form, fund_code: e.target.value })}>
              {FUNDS.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
            </select></label>
          <label className="text-sm">份额<input className={`${input} w-24`} value={form.shares}
            onChange={(e) => setForm({ ...form, shares: e.target.value })} /></label>
          <label className="text-sm">确认净值<input className={`${input} w-24`} value={form.nav}
            onChange={(e) => setForm({ ...form, nav: e.target.value })} /></label>
          <label className="text-sm">理由代码
            <select className={input} value={form.reason_code}
              onChange={(e) => setForm({ ...form, reason_code: e.target.value })}>
              {Object.entries(REASON_LABELS).filter(([c]) => c !== "N0").map(([c, l]) =>
                <option key={c} value={c}>{c} {l}</option>)}
            </select></label>
          <label className="text-sm">费用估计<input className={`${input} w-20`} value={form.fee_estimate}
            onChange={(e) => setForm({ ...form, fee_estimate: e.target.value })} /></label>
        </>}
        <label className="text-sm">金额<input required className={`${input} w-28`} value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
        <label className="text-sm">备注<input className={`${input} w-40`} value={form.note}
          onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
        <Button type="submit">记录</Button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <table className="w-full text-sm border">
        <thead><tr className="bg-muted text-left">
          {["日期", "方向", "基金", "金额", "份额", "净值", "理由", "费用", "备注"].map((h) =>
            <th key={h} className="p-2">{h}</th>)}
        </tr></thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-t">
              <td className="p-2">{t.date}</td>
              <td className="p-2">{DIRECTION_LABELS[t.direction]}</td>
              <td className="p-2">{t.fund_code ?? "—"}</td>
              <td className="p-2">{t.amount.toLocaleString("zh-CN")}</td>
              <td className="p-2">{t.shares ?? "—"}</td>
              <td className="p-2">{t.nav ?? "—"}</td>
              <td className="p-2">{t.reason_code ?? "—"}</td>
              <td className="p-2">{t.fee_estimate ?? "—"}</td>
              <td className="p-2">{t.note ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
