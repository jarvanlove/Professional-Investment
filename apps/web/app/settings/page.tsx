"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Settings } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Eye, EyeOff, Copy, Check, Loader2, Settings as SettingsIcon } from "lucide-react";
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

export default function SettingsPage() {
  const [form, setForm] = useState<Settings | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [models, setModels] = useState<{ value: string; label: string }[]>(() => normalizeOptions(PROVIDERS[0].defaults));
  const [loadingModels, setLoadingModels] = useState(false);

  useEffect(() => {
    api.settings().then((s) => {
      const current = PROVIDERS.find((p) => p.id === s.llm_provider) ?? PROVIDERS[0];
      if (!s.llm_api_key && current.keyField) {
        s = { ...s, llm_api_key: s[current.keyField] ?? "" };
      }
      setForm(s);
      setModels(normalizeOptions(defaultsFor(s.llm_provider)));
    }).catch((e) => setError(String(e)));
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

  async function save(e: React.FormEvent) {
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

  if (error && !form) return <main className="p-8 text-red-600">加载失败：{error}</main>;
  if (!form) return <main className="p-8">加载中…</main>;

  return (
    <main className="p-8 space-y-6">
      <PageHeader
        icon={SettingsIcon}
        title="设置"
        description="配置 LLM 供应商与模型，用于 AI 信号解读。"
      />

      <form onSubmit={save}>
        <div className="grid lg:grid-cols-12 gap-6 items-start">
          <Card className="lg:col-span-5">
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

          <Card className="lg:col-span-7">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">连接配置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
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

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t">
                <div className="min-h-[1.5rem]">
                  {message && <span className="text-sm text-success">{message}</span>}
                  {error && <p className="text-sm text-destructive">{error}</p>}
                </div>
                <Button type="submit" size="default">保存设置</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </form>
    </main>
  );
}
