"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { InterpretResult } from "@/lib/api";
import type { SignalReport } from "@/lib/types";
import { REGIME_LABELS } from "@/lib/types";
import { DecisionCard } from "@/components/DecisionCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STEPS = ["更新净值", "计算信号", "按建议到场外平台下单", "回来补录交易日志"];

export default function SignalsPage() {
  const [report, setReport] = useState<SignalReport | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [interp, setInterp] = useState<InterpretResult | null>(null);
  const [interpError, setInterpError] = useState<string | null>(null);

  useEffect(() => {
    api.latestSignals().then(setReport).catch(() => setReport(null));
  }, []);

  async function refreshNav() {
    setBusy("nav"); setMessage(null);
    try {
      const r = await api.refreshNav();
      const failed = r.results.filter((x) => x.status !== "ok");
      setMessage(failed.length
        ? `部分抓取失败：${failed.map((x) => x.code).join("、")}——可手动导入净值兜底`
        : `净值已更新（${r.results.map((x) => `${x.code}+${x.added}`).join("，")}）`);
    } catch (e) { setMessage(`抓取失败：${e}`); }
    setBusy(null);
  }

  async function compute() {
    setBusy("compute"); setMessage(null);
    try { setReport(await api.computeSignals()); }
    catch (e) { setMessage(`计算失败：${e}`); }
    setBusy(null);
  }

  async function interpret() {
    setBusy("interpret"); setInterpError(null);
    try { setInterp(await api.interpret()); }
    catch (e) { setInterpError(String(e)); }
    setBusy(null);
  }

  return (
    <main className="p-8 space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-xl font-bold">每周信号</h1>
        <Button onClick={refreshNav} disabled={busy !== null}>{busy === "nav" ? "抓取中…" : "1. 更新净值"}</Button>
        <Button onClick={compute} disabled={busy !== null} variant="secondary">{busy === "compute" ? "计算中…" : "2. 计算信号"}</Button>
        <Button onClick={interpret} disabled={busy !== null} variant="outline">
          {busy === "interpret" ? "解读中…" : "AI 解读"}
        </Button>
        {report && <Badge>{REGIME_LABELS[report.regime]}模式 · {report.as_of}</Badge>}
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-1.5 border rounded-full px-2.5 py-1">
            <span className="inline-flex size-4 items-center justify-center rounded-full bg-primary text-primary-foreground text-[10px]">{i + 1}</span>
            {s}
          </div>
        ))}
      </div>
      {message && <p className="text-sm text-amber-700">{message}</p>}
      {report?.account_actions.map((a, i) => (
        <p key={i} className="text-sm font-medium text-red-700 border border-red-200 bg-red-50 rounded p-2">{a}</p>
      ))}
      {report ? (
        <>
          <p className="text-sm text-muted-foreground">
            组合回撤 {(report.portfolio_dd * 100).toFixed(1)}% · 现金 {(report.cash_weight * 100).toFixed(1)}%
            · 本周单元预算 {report.weekly_unit_budget} 个 · 成交净值以确认日为准（未知价原则）
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {report.decisions.map((d) => <DecisionCard key={d.code} d={d} />)}
          </div>
        </>
      ) : (
        <p className="text-muted-foreground">尚无信号。先"更新净值"，再"计算信号"。没有信号时持有现金是正确动作（N0）。</p>
      )}
      {interpError && (
        <Card className="border-red-200">
          <CardContent className="pt-4 text-sm text-red-700">
            AI 解读失败：{interpError}
            {interpError.includes("未配置") && (
              <a href="/settings" className="underline ml-2">前往设置页</a>
            )}
          </CardContent>
        </Card>
      )}
      {interp && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">AI 解读（{interp.model} · {interp.as_of}）</CardTitle>
          </CardHeader>
          <CardContent className="text-sm whitespace-pre-wrap">{interp.text}</CardContent>
        </Card>
      )}
    </main>
  );
}
