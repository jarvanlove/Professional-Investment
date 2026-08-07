"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Settings } from "@/lib/api";
import type { DcaPlan } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Eye, EyeOff, Copy, Check, Loader2, Settings as SettingsIcon, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { cn } from "@/lib/utils";

interface Provider {
  id: string;
  name: string;
  baseUrl: string;
  logo: string;
  keyField: keyof Settings;
  defaults: string[];
}

const PROVIDERS: Provider[] = [
  {
    id: "deepseek", name: "DeepSeek", baseUrl: "https://api.deepseek.com",
    logo: "/logos/deepseek.svg", keyField: "deepseek_api_key",
    defaults: ["deepseek-v4-pro", "deepseek-v4-flash"],
  },
  {
    id: "kimi", name: "Kimi", baseUrl: "https://api.moonshot.ai/v1",
    logo: "/logos/kimi.svg", keyField: "kimi_api_key",
    defaults: ["kimi-k3", "kimi-k2.7-code"],
  },
  {
    id: "kimi-coding", name: "Kimi For Coding", baseUrl: "https://api.kimi.com/coding/v1",
    logo: "/logos/kimi.svg", keyField: "kimi_api_key",
    defaults: ["kimi-k2.7-code", "kimi-k3"],
  },
  {
    id: "minimax", name: "MiniMax", baseUrl: "https://api.minimax.io/v1",
    logo: "/logos/minimax.svg", keyField: "minimax_api_key",
    defaults: ["MiniMax-M3", "MiniMax-M2.7"],
  },
  {
    id: "minimax-cn", name: "MiniMax 国内", baseUrl: "https://api.minimaxi.com/v1",
    logo: "/logos/minimax.svg", keyField: "minimax_api_key",
    defaults: ["MiniMax-M3", "MiniMax-M2.7"],
  },
  {
    id: "qwen", name: "Qwen", baseUrl: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    logo: "/logos/qwen.svg", keyField: "qwen_api_key",
    defaults: ["qwen3.8-max", "qwen3.7-plus"],
  },
  {
    id: "qwen-coding", name: "Qwen Code", baseUrl: "https://coding.dashscope.aliyuncs.com/v1",
    logo: "/logos/qwen.svg", keyField: "qwen_api_key",
    defaults: ["qwen3-coder-plus"],
  },
  {
    id: "qwen-cn", name: "通义千问", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    logo: "/logos/qwen.svg", keyField: "qwen_api_key",
    defaults: ["qwen3.8-max", "qwen3.7-plus"],
  },
  {
    id: "glm", name: "GLM", baseUrl: "https://api.z.ai/api/paas/v4",
    logo: "/logos/glm.svg", keyField: "glm_api_key",
    defaults: ["glm-5.2", "glm-4.7"],
  },
  {
    id: "glm-coding", name: "GLM Coding", baseUrl: "https://api.z.ai/api/coding/paas/v4",
    logo: "/logos/glm.svg", keyField: "glm_api_key",
    defaults: ["glm-5.2", "glm-4.7"],
  },
];

const FUNDS = [
  { code: "001480", name: "财通成长优选混合A" },
  { code: "025343", name: "长盛上证科创板芯片指数C" },
  { code: "027521", name: "广发科创芯片设计ETF联接C" },
  { code: "005052", name: "摩根标普港股通低波红利指数C" },
];

const WEEKDAYS = ["周一", "周二", "周三", "周四", "周五"];

type TabKey = "model" | "quant";

function defaultsFor(id: string) {
  return PROVIDERS.find((p) => p.id === id)?.defaults ?? PROVIDERS[0].defaults;
}

function normalizeOptions(models: string[]) {
  return models.map((id) => ({ value: id, label: id }));
}

function ProviderBadge({ p, active, onClick }: { p: Provider; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex flex-col items-center justify-center gap-2 rounded-lg border px-2 py-3 text-center text-xs transition-all min-h-[6rem] relative overflow-hidden",
        active
          ? "border-l-4 border-l-primary border-y-border border-r-border bg-accent/60 text-foreground shadow-sm"
          : "border-border bg-surface hover:bg-surface-subtle hover:border-border/80"
      )}
    >
      <img src={p.logo} alt={p.name} className="h-7 w-auto object-contain opacity-90 group-hover:opacity-100" />
      <span className="leading-tight font-medium">{p.name}</span>
      {active && <span className="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-primary" aria-hidden />}
    </button>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {children}
    </div>
  );
}

function parseBaseWeights(raw: string) {
  try {
    return JSON.parse(raw) as Record<string, number>;
  } catch {
    return {};
  }
}

export default function SettingsPage() {
  const [form, setForm] = useState<Settings | null>(null);
  const [tab, setTab] = useState<TabKey>("model");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [models, setModels] = useState<{ value: string; label: string }[]>(() => normalizeOptions(PROVIDERS[0].defaults));
  const [loadingModels, setLoadingModels] = useState(false);

  const [plans, setPlans] = useState<DcaPlan[]>([]);
  const [baseWeights, setBaseWeights] = useState<Record<string, number>>({});
  const [newPlan, setNewPlan] = useState<Omit<DcaPlan, "id">>({
    fund_code: "001480", frequency: "weekly", amount: 1000,
    day_of_week: 4, day_of_month: null, active: true, note: "",
  });

  useEffect(() => {
    api.settings().then((s) => {
      const current = PROVIDERS.find((p) => p.id === s.llm_provider) ?? PROVIDERS[0];
      if (!s.llm_api_key && current.keyField) {
        s = { ...s, llm_api_key: s[current.keyField] ?? "" };
      }
      setForm(s);
      setModels(normalizeOptions(defaultsFor(s.llm_provider)));
      setBaseWeights(parseBaseWeights(s.strategy_base_weights));
    }).catch((e) => setError(String(e)));
    api.dcaPlans().then(setPlans).catch(() => setPlans([]));
  }, []);

  function selectProvider(id: string) {
    const p = PROVIDERS.find((x) => x.id === id);
    if (!p || !form) return;
    const current = PROVIDERS.find((x) => x.id === form.llm_provider);
    const nextKey = form[p.keyField] ?? "";
    setModels(normalizeOptions(p.defaults));
    setForm({
      ...form,
      ...(current ? { [current.keyField]: form.llm_api_key } : {}),
      llm_provider: id,
      llm_base_url: p.baseUrl,
      llm_api_key: nextKey,
      llm_model: p.defaults[0] ?? "",
    });
  }

  async function saveSettings(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setMessage(null); setError(null);
    try {
      setForm(await api.saveSettings(form));
      setMessage("设置已保存，立即生效。");
    } catch (err) { setError(String(err)); }
  }

  async function copyKey() {
    if (!form?.llm_api_key) return;
    await navigator.clipboard.writeText(form.llm_api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function fetchModels() {
    if (!form) return;
    setLoadingModels(true);
    setError(null);
    try {
      const { models: ids } = await api.models(form.llm_base_url, form.llm_api_key);
      const opts = normalizeOptions(ids.length > 0 ? ids : defaultsFor(form.llm_provider));
      setModels(opts);
      setForm((prev) => {
        if (!prev) return prev;
        const valid = ids.length > 0 ? ids : defaultsFor(prev.llm_provider);
        return { ...prev, llm_model: valid.includes(prev.llm_model) ? prev.llm_model : valid[0] };
      });
      setMessage(`已获取 ${ids.length} 个模型。`);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoadingModels(false);
    }
  }

  function updateBaseWeight(code: string, pct: string) {
    const val = Math.max(0, Math.min(100, parseFloat(pct) || 0));
    const next = { ...baseWeights, [code]: val / 100 };
    setBaseWeights(next);
    setForm((prev) => prev && { ...prev, strategy_base_weights: JSON.stringify(next) });
  }

  async function addPlan() {
    setError(null);
    try {
      await api.createDcaPlan(newPlan);
      setPlans(await api.dcaPlans());
      setNewPlan({ fund_code: "001480", frequency: "weekly", amount: 1000,
                   day_of_week: 4, day_of_month: null, active: true, note: "" });
      setMessage("定投计划已添加。");
    } catch (err) { setError(String(err)); }
  }

  async function togglePlan(plan: DcaPlan) {
    if (plan.id == null) return;
    try {
      await api.updateDcaPlan(plan.id, { ...plan, active: !plan.active });
      setPlans(await api.dcaPlans());
    } catch (err) { setError(String(err)); }
  }

  async function deletePlan(id: number) {
    try {
      await api.deleteDcaPlan(id);
      setPlans(await api.dcaPlans());
    } catch (err) { setError(String(err)); }
  }

  if (error && !form) return <main className="p-8 text-red-600">加载失败：{error}</main>;
  if (!form) return <main className="p-8">加载中…</main>;

  return (
    <main className="p-8 space-y-6">
      <PageHeader
        icon={SettingsIcon}
        title="设置"
        description="配置 LLM 供应商、量化策略参数与定投计划。"
      />

      <div className="flex items-center gap-1 rounded-lg border bg-muted p-1 w-fit">
        <button
          type="button"
          onClick={() => setTab("model")}
          className={cn(
            "px-4 py-1.5 text-sm rounded-md transition-colors",
            tab === "model" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
          )}
        >
          模型配置
        </button>
        <button
          type="button"
          onClick={() => setTab("quant")}
          className={cn(
            "px-4 py-1.5 text-sm rounded-md transition-colors",
            tab === "quant" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
          )}
        >
          量化参数配置
        </button>
      </div>

      {(message || error) && (
        <div className="min-h-[1.5rem]">
          {message && <span className="text-sm text-success">{message}</span>}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
      )}

      {tab === "model" && (
        <form onSubmit={saveSettings} className="grid lg:grid-cols-12 gap-6">
          <Card className="lg:col-span-5 h-full flex flex-col">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">选择供应商</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-muted-foreground leading-relaxed">
                点击卡片切换 Base URL 与模型，并自动恢复该供应商已保存的 API Key。通用版与 Coding 版共用同一 Key 字段。
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {PROVIDERS.map((p) => (
                  <ProviderBadge
                    key={p.id}
                    p={p}
                    active={form.llm_provider === p.id}
                    onClick={() => selectProvider(p.id)}
                  />
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-7 h-full flex flex-col">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">连接配置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6 flex-1">
              <Section title="端点地址">
                <Input id="url" value={form.llm_base_url}
                  onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
                  placeholder="https://api.example.com/v1" />
              </Section>

              <Section title="API Key">
                <div className="relative">
                  <Input id="key" type={showKey ? "text" : "password"} value={form.llm_api_key}
                    onChange={(e) => setForm({ ...form, llm_api_key: e.target.value })}
                    placeholder="sk-..."
                    className="pr-[4.5rem]" />
                  <div className="absolute inset-y-0 right-1 flex items-center gap-0.5">
                    <Button type="button" variant="ghost" size="icon-sm"
                      onClick={() => setShowKey((s) => !s)}
                      title={showKey ? "隐藏 Key" : "显示 Key"}>
                      {showKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    </Button>
                    <Button type="button" variant="ghost" size="icon-sm"
                      onClick={copyKey}
                      disabled={!form.llm_api_key}
                      title="复制 Key">
                      {copied ? <Check className="size-4 text-success" /> : <Copy className="size-4" />}
                    </Button>
                  </div>
                </div>
              </Section>

              <Section title="模型">
                <div className="flex items-center gap-3">
                  <Select value={form.llm_model}
                    onValueChange={(v) => v && setForm({ ...form, llm_model: v })}>
                    <SelectTrigger id="model" className="w-full"><SelectValue placeholder="选择模型" /></SelectTrigger>
                    <SelectContent>
                      {models.map((m) => (
                        <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button type="button" variant="outline" size="sm"
                    onClick={fetchModels}
                    disabled={loadingModels}>
                    {loadingModels && <Loader2 className="mr-1 size-3 animate-spin" />}
                    获取模型列表
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  点击“获取模型列表”会使用上方 Base URL 和 API Key 实时拉取对应供应商的模型。
                </p>
              </Section>
            </CardContent>
          </Card>

          <div className="lg:col-span-12 flex justify-end">
            <Button type="submit" size="default">保存模型设置</Button>
          </div>
        </form>
      )}

      {tab === "quant" && (
        <form onSubmit={saveSettings} className="grid lg:grid-cols-12 gap-6">
          <Card className="lg:col-span-6 h-full flex flex-col">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">量化策略参数</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 flex-1">
              <Section title="底仓权重（%）">
                <div className="grid grid-cols-2 gap-3">
                  {FUNDS.map((f) => (
                    <div key={f.code} className="space-y-1">
                      <Label className="text-xs text-muted-foreground">{f.name} <span className="font-mono">{f.code}</span></Label>
                      <Input
                        type="number"
                        min={0}
                        max={100}
                        step={0.1}
                        value={((baseWeights[f.code] ?? 0) * 100).toFixed(1)}
                        onChange={(e) => updateBaseWeight(f.code, e.target.value)}
                      />
                    </div>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">底仓是每只基金的最小保留权重，卖出建议不会跌破该底线。</p>
              </Section>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">单次最大卖出比例</Label>
                  <Input type="number" min={0.01} max={1} step={0.01}
                    value={form.strategy_max_sell_ratio}
                    onChange={(e) => setForm({ ...form, strategy_max_sell_ratio: e.target.value })} />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">权重缓冲带（pp）</Label>
                  <Input type="number" min={0} max={0.1} step={0.001}
                    value={form.strategy_buffer_pp}
                    onChange={(e) => setForm({ ...form, strategy_buffer_pp: e.target.value })} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">赎回费规避阈值</Label>
                  <Input type="number" min={0} max={0.05} step={0.001}
                    value={form.strategy_fee_aversion}
                    onChange={(e) => setForm({ ...form, strategy_fee_aversion: e.target.value })} />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">置信度缩放</Label>
                  <Select value={form.strategy_confidence_scaling}
                    onValueChange={(v) => v != null && setForm({ ...form, strategy_confidence_scaling: v })}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">开启</SelectItem>
                      <SelectItem value="0">关闭</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-6 h-full flex flex-col">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">定投计划</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 flex-1">
              {plans.length > 0 && (
                <div className="space-y-2">
                  {plans.map((p) => (
                    <div key={p.id} className="flex items-center justify-between rounded-lg border p-3">
                      <div className="text-sm">
                        <div className="font-medium">{FUNDS.find((f) => f.code === p.fund_code)?.name ?? p.fund_code}</div>
                        <div className="text-xs text-muted-foreground">
                          {p.frequency === "weekly" ? `每周${WEEKDAYS[p.day_of_week ?? 0]}` : `每月${p.day_of_month}日`} · ¥{p.amount}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => togglePlan(p)}
                          className={cn(
                            "px-2 py-1 rounded text-xs border",
                            p.active
                              ? "bg-buy/10 text-buy border-buy/30"
                              : "bg-muted text-muted-foreground border-border"
                          )}
                        >
                          {p.active ? "启用" : "暂停"}
                        </button>
                        <Button type="button" variant="ghost" size="icon-sm"
                          onClick={() => p.id != null && deletePlan(p.id)}>
                          <Trash2 className="size-4 text-sell" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="space-y-3 border-t pt-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">基金</Label>
                    <Select value={newPlan.fund_code}
                      onValueChange={(v) => v != null && setNewPlan({ ...newPlan, fund_code: v })}>
                      <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {FUNDS.map((f) => <SelectItem key={f.code} value={f.code}>{f.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">频率</Label>
                    <Select value={newPlan.frequency}
                      onValueChange={(v) => {
                        if (v == null) return;
                        setNewPlan({
                          ...newPlan, frequency: v,
                          day_of_week: v === "weekly" ? 4 : null,
                          day_of_month: v === "monthly" ? 1 : null,
                        });
                      }}>
                      <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="weekly">每周</SelectItem>
                        <SelectItem value="monthly">每月</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">{newPlan.frequency === "weekly" ? "周几" : "日期（1-28）"}</Label>
                    {newPlan.frequency === "weekly" ? (
                      <Select value={String(newPlan.day_of_week ?? 0)}
                        onValueChange={(v) => v != null && setNewPlan({ ...newPlan, day_of_week: parseInt(v, 10) })}>
                        <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {WEEKDAYS.map((d, i) => <SelectItem key={i} value={String(i)}>{d}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input type="number" min={1} max={28} step={1} className="w-full"
                        value={newPlan.day_of_month ?? 1}
                        onChange={(e) => setNewPlan({ ...newPlan, day_of_month: parseInt(e.target.value, 10) || 1 })} />
                    )}
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">金额（¥）</Label>
                    <Input type="number" min={1} step={1} className="w-full"
                      value={newPlan.amount}
                      onChange={(e) => setNewPlan({ ...newPlan, amount: parseFloat(e.target.value) || 0 })} />
                  </div>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={addPlan}>添加定投计划</Button>
              </div>
            </CardContent>
          </Card>

          <div className="lg:col-span-12 flex justify-end">
            <Button type="submit" size="default">保存量化参数</Button>
          </div>
        </form>
      )}
    </main>
  );
}
