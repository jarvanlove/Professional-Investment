"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { InterpretResult, NavRow } from "@/lib/api";
import type { SignalReport } from "@/lib/types";
import { REGIME_LABELS } from "@/lib/types";
import { DecisionCard } from "@/components/DecisionCard";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TrendingUp, ChevronRight, Loader2, Upload } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = ["更新净值", "计算信号", "按建议到场外平台下单", "回来补录交易日志"];

const IMPORT_OPTIONS: [string, string][] = [
  ["001480", "001480 财通成长优选混合A"],
  ["025343", "025343 长盛上证科创板芯片指数C"],
  ["027521", "027521 广发科创芯片设计ETF联接C"],
  ["005052", "005052 摩根标普港股通低波红利指数C"],
  ["589210", "589210 广发科创芯片ETF（027521 信号代理）"],
];

const REGIME_TONE: Record<string, string> = {
  attack: "border-buy/30 bg-buy/5 text-buy",
  neutral: "border-primary/30 bg-primary/5 text-primary",
  protect: "border-amber-500/30 bg-amber-500/10 text-amber-700",
  defense: "border-sell/30 bg-sell/8 text-sell",
};

export default function SignalsPage() {
  const [report, setReport] = useState<SignalReport | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [failedCodes, setFailedCodes] = useState<string[]>([]);
  const [interp, setInterp] = useState<InterpretResult | null>(null);
  const [interpError, setInterpError] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [importCode, setImportCode] = useState<string>("589210");
  const [importText, setImportText] = useState<string>("");
  const [importMsg, setImportMsg] = useState<string | null>(null);

  useEffect(() => {
    api.latestSignals().then(setReport).catch(() => setReport(null));
  }, []);

  useEffect(() => {
    if (failedCodes.length > 0 && failedCodes.includes(importCode)) {
      // keep current if it's one of the failed ones
      return;
    }
    if (failedCodes.length > 0) {
      setImportCode(failedCodes[0]);
    }
  }, [failedCodes]);

  async function refreshNav() {
    setBusy("nav"); setMessage(null); setFailedCodes([]);
    try {
      const r = await api.refreshNav();
      const failed = r.results.filter((x) => x.status !== "ok");
      setFailedCodes(failed.map((x) => x.code));
      setMessage(failed.length
        ? `部分抓取失败：${failed.map((x) => x.code).join("、")}`
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

  function parseNavRows(text: string): NavRow[] | string {
    const rows: NavRow[] = [];
    const lines = text.trim().split(/\r?\n/).filter((l) => l.trim());
    for (const line of lines) {
      const parts = line.split(/[,，\t]+/);
      if (parts.length < 2) return `格式错误：${line}`;
      const date = parts[0].trim();
      const nav = parseFloat(parts[1].trim());
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return `日期格式错误：${date}`;
      if (Number.isNaN(nav) || nav <= 0) return `净值无效：${parts[1].trim()}`;
      rows.push({ date, nav });
    }
    return rows;
  }

  async function submitImport() {
    setImportMsg(null);
    const parsed = parseNavRows(importText);
    if (typeof parsed === "string") { setImportMsg(parsed); return; }
    if (parsed.length === 0) { setImportMsg("请输入至少一行数据"); return; }
    setBusy("import");
    try {
      const r = await api.importNav(importCode, parsed);
      setImportMsg(`已导入 ${r.added} 条净值到 ${importCode}`);
      setImportText("");
      setFailedCodes((prev) => prev.filter((c) => c !== importCode));
    } catch (e) {
      setImportMsg(`导入失败：${e}`);
    }
    setBusy(null);
  }

  return (
    <main className="p-8 space-y-6">
      <PageHeader
        icon={TrendingUp}
        title="每周信号"
        description="更新净值 → 计算信号 → 按建议下单 → 补录日志。"
      />

      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={refreshNav} disabled={busy !== null}>
          {busy === "nav" && <Loader2 className="size-4 animate-spin" />}
          {busy === "nav" ? "抓取中…" : "1. 更新净值"}
        </Button>
        <Button onClick={compute} disabled={busy !== null} variant="secondary">
          {busy === "compute" && <Loader2 className="size-4 animate-spin" />}
          {busy === "compute" ? "计算中…" : "2. 计算信号"}
        </Button>
        <Button onClick={interpret} disabled={busy !== null || !report} variant="outline">
          {busy === "interpret" && <Loader2 className="size-4 animate-spin" />}
          {busy === "interpret" ? "解读中…" : "AI 解读"}
        </Button>
      </div>

      {showImport && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">手动导入净值</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              当自动抓取失败时，可粘贴基金净值。每行一条，格式：<code className="rounded bg-muted px-1 py-0.5">YYYY-MM-DD, 净值</code>。
            </p>
            <div className="grid gap-3 md:grid-cols-[260px_1fr]">
              <div className="space-y-1">
                <Label>目标基金</Label>
                <Select value={importCode} onValueChange={(v) => setImportCode(v ?? "589210")}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {IMPORT_OPTIONS.map(([c, l]) => (
                      <SelectItem key={c} value={c}>{l}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>净值数据</Label>
                <Textarea
                  rows={6}
                  placeholder={`2026-08-01, 1.2345\n2026-08-04, 1.2456`}
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={submitImport} disabled={busy !== null}>
                {busy === "import" && <Loader2 className="size-4 animate-spin" />}
                确认导入
              </Button>
              {importMsg && (
                <p className={cn("text-sm", importMsg.startsWith("已导入") ? "text-buy" : "text-sell")}>{importMsg}</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-1 text-xs">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-1">
            <div className="flex items-center gap-1.5 rounded-full border bg-surface px-2.5 py-1">
              <span className="inline-flex size-4 items-center justify-center rounded-full bg-primary text-primary-foreground text-[10px]">{i + 1}</span>
              {s}
            </div>
            {i < STEPS.length - 1 && <ChevronRight className="size-3.5 text-muted-foreground" />}
          </div>
        ))}
      </div>

      {message && (
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm text-amber-700">{message}</p>
          {failedCodes.length > 0 && (
            <Button onClick={() => setShowImport(true)} disabled={busy !== null} variant="outline" size="sm">
              <Upload className="size-4 mr-1" />
              手动导入净值
            </Button>
          )}
        </div>
      )}
      {report?.account_actions.map((a, i) => (
        <p key={i} className="text-sm font-medium text-buy border border-buy/30 bg-buy/5 rounded-lg p-2.5">{a}</p>
      ))}

      {report ? (
        <>
          <Card className={cn("border", REGIME_TONE[report.regime] ?? "border-primary/30 bg-primary/5 text-primary")}>
            <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-1 pt-4 text-sm">
              <span className="text-base font-bold">{REGIME_LABELS[report.regime]}模式 · {report.as_of}</span>
              <span className="tabular-nums">组合回撤 {(report.portfolio_dd * 100).toFixed(1)}%</span>
              <span className="tabular-nums">现金 {(report.cash_weight * 100).toFixed(1)}%</span>
              <span className="tabular-nums">本周单元预算 {report.weekly_unit_budget} 个</span>
              <span className="text-xs opacity-80">成交净值以确认日为准（未知价原则）</span>
            </CardContent>
          </Card>
          <div className="grid md:grid-cols-2 gap-4">
            {report.decisions.map((d) => <DecisionCard key={d.code} d={d} />)}
          </div>
        </>
      ) : (
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            尚无信号。先"更新净值"，再"计算信号"。没有信号时持有现金是正确动作（N0）。
          </CardContent>
        </Card>
      )}

      {interpError && (
        <Card className="border-buy/30">
          <CardContent className="pt-4 text-sm text-buy">
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
          <CardContent className="text-sm whitespace-pre-wrap leading-relaxed">{interp.text}</CardContent>
        </Card>
      )}
    </main>
  );
}
