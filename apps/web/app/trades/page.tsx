"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Trade } from "@/lib/types";
import { REASON_LABELS } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
  const [ok, setOk] = useState(false);
  const isFundTrade = form.direction === "buy" || form.direction === "sell";

  const load = () => api.trades().then(setTrades).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null); setOk(false);
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
      setOk(true);
      load();
    } catch (err) { setError(String(err)); }
  }

  return (
    <main className="p-8 space-y-6">
      <h1 className="text-xl font-bold">交易日志</h1>
      <Card>
        <CardHeader><CardTitle className="text-base">录入</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
            <div className="space-y-1">
              <Label>日期</Label>
              <Input type="date" value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label>方向</Label>
              <Select value={form.direction}
                onValueChange={(v) => setForm({ ...form, direction: v as string })}>
                <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(DIRECTION_LABELS).map(([v, l]) =>
                    <SelectItem key={v} value={v}>{l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {isFundTrade && <>
              <div className="space-y-1">
                <Label>基金</Label>
                <Select value={form.fund_code}
                  onValueChange={(v) => setForm({ ...form, fund_code: v as string })}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {FUNDS.map(([c, n]) => <SelectItem key={c} value={c}>{n}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>份额</Label>
                <Input value={form.shares}
                  onChange={(e) => setForm({ ...form, shares: e.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>确认净值</Label>
                <Input value={form.nav}
                  onChange={(e) => setForm({ ...form, nav: e.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>理由代码</Label>
                <Select value={form.reason_code}
                  onValueChange={(v) => setForm({ ...form, reason_code: v as string })}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(REASON_LABELS).filter(([c]) => c !== "N0").map(([c, l]) =>
                      <SelectItem key={c} value={c}>{c} {l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>费用估计</Label>
                <Input value={form.fee_estimate}
                  onChange={(e) => setForm({ ...form, fee_estimate: e.target.value })} />
              </div>
            </>}
            <div className="space-y-1">
              <Label>金额</Label>
              <Input required value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label>备注</Label>
              <Input value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </div>
            <div><Button type="submit">记录</Button></div>
          </form>
          {ok && <p className="text-sm text-green-700 mt-3">已记录。</p>}
          {error && <p className="text-sm text-red-600 mt-3">{error}</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">记录列表</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                {["日期", "方向", "基金", "金额", "份额", "净值", "理由", "费用", "备注"].map((h) =>
                  <TableHead key={h}>{h}</TableHead>)}
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>{t.date}</TableCell>
                  <TableCell>{DIRECTION_LABELS[t.direction]}</TableCell>
                  <TableCell>{t.fund_code ?? "—"}</TableCell>
                  <TableCell>{t.amount.toLocaleString("zh-CN")}</TableCell>
                  <TableCell>{t.shares ?? "—"}</TableCell>
                  <TableCell>{t.nav ?? "—"}</TableCell>
                  <TableCell>{t.reason_code ?? "—"}</TableCell>
                  <TableCell>{t.fee_estimate ?? "—"}</TableCell>
                  <TableCell>{t.note ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </main>
  );
}
