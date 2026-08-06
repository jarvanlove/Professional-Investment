"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Settings } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Eye, EyeOff, Copy, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Provider {
  id: string;
  name: string;
  baseUrl: string;
  badge: string;
  color: string;
}

const PROVIDERS: Provider[] = [
  { id: "deepseek", name: "DeepSeek", baseUrl: "https://api.deepseek.com", badge: "D", color: "bg-blue-600" },
  { id: "kimi", name: "Kimi", baseUrl: "https://api.moonshot.ai/v1", badge: "K", color: "bg-sky-500" },
  { id: "kimi-coding", name: "Kimi For Coding", baseUrl: "https://api.kimi.com/coding/v1", badge: "K", color: "bg-indigo-600" },
  { id: "minimax", name: "MiniMax", baseUrl: "https://api.minimax.io/v1", badge: "M", color: "bg-red-500" },
  { id: "minimax-cn", name: "MiniMax 国内", baseUrl: "https://api.minimaxi.com/v1", badge: "M", color: "bg-orange-500" },
  { id: "qwen", name: "Qwen", baseUrl: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", badge: "Q", color: "bg-purple-600" },
  { id: "qwen-coding", name: "Qwen Code", baseUrl: "https://coding.dashscope.aliyuncs.com/v1", badge: "Q", color: "bg-fuchsia-600" },
  { id: "qwen-cn", name: "通义千问", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", badge: "Q", color: "bg-violet-600" },
  { id: "glm", name: "GLM", baseUrl: "https://api.z.ai/api/paas/v4", badge: "G", color: "bg-emerald-600" },
  { id: "glm-coding", name: "GLM Coding", baseUrl: "https://api.z.ai/api/coding/paas/v4", badge: "G", color: "bg-teal-600" },
];

const DEFAULT_MODELS = [
  { value: "deepseek-v4-pro", label: "deepseek-v4-pro（最新推荐）" },
  { value: "deepseek-v4-flash", label: "deepseek-v4-flash（更快更便宜）" },
];

function normalizeOptions(models: string[]) {
  return models.map((id) => ({ value: id, label: id }));
}

function ProviderBadge({ p, active, onClick }: { p: Provider; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left text-sm transition-colors",
        active
          ? "border-primary bg-primary/10 text-primary"
          : "border-input bg-background hover:bg-muted"
      )}
    >
      <span className={cn("inline-flex size-6 shrink-0 items-center justify-center rounded-md text-xs font-bold text-white", p.color)}>
        {p.badge}
      </span>
      <span className="truncate">{p.name}</span>
    </button>
  );
}

export default function SettingsPage() {
  const [form, setForm] = useState<Settings | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [models, setModels] = useState<{ value: string; label: string }[]>(DEFAULT_MODELS);
  const [loadingModels, setLoadingModels] = useState(false);

  useEffect(() => {
    api.settings().then(setForm).catch((e) => setError(String(e)));
  }, []);

  function selectProvider(id: string) {
    const p = PROVIDERS.find((x) => x.id === id);
    if (!p || !form) return;
    setForm({ ...form, llm_provider: id, llm_base_url: p.baseUrl });
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setMessage(null); setError(null);
    try {
      setForm(await api.saveSettings(form));
      setMessage("已保存，立即生效。");
    } catch (err) { setError(String(err)); }
  }

  async function copyKey() {
    if (!form?.llm_api_key) return;
    await navigator.clipboard.writeText(form.llm_api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function fetchModels() {
    setLoadingModels(true);
    setError(null);
    try {
      const { models: ids } = await api.models();
      const opts = normalizeOptions(ids.length > 0 ? ids : DEFAULT_MODELS.map((m) => m.value));
      setModels(opts);
      setForm((prev) => {
        if (!prev) return prev;
        const current = prev.llm_model;
        const valid = ids.length > 0 ? ids : DEFAULT_MODELS.map((m) => m.value);
        return { ...prev, llm_model: valid.includes(current) ? current : valid[0] };
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
      <h1 className="text-xl font-bold">设置</h1>
      <Card className="max-w-3xl">
        <CardHeader><CardTitle className="text-base">LLM（AI 解读）</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={save} className="space-y-5">
            <div className="space-y-2">
              <Label>供应商</Label>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                {PROVIDERS.map((p) => (
                  <ProviderBadge
                    key={p.id}
                    p={p}
                    active={form.llm_provider === p.id}
                    onClick={() => selectProvider(p.id)}
                  />
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                点击卡片自动填充对应 Base URL；通用版与 Coding 版使用不同的 endpoint，请搭配对应的 API Key。
              </p>
            </div>

            <div className="space-y-1">
              <Label htmlFor="url">Base URL</Label>
              <Input id="url" value={form.llm_base_url}
                onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })} />
            </div>

            <div className="space-y-1">
              <Label htmlFor="key">API Key</Label>
              <div className="relative">
                <Input id="key" type={showKey ? "text" : "password"} value={form.llm_api_key}
                  onChange={(e) => setForm({ ...form, llm_api_key: e.target.value })}
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
                    {copied ? <Check className="size-4 text-green-600" /> : <Copy className="size-4" />}
                  </Button>
                </div>
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <Label htmlFor="model">模型</Label>
                <Button type="button" variant="outline" size="xs"
                  onClick={fetchModels}
                  disabled={loadingModels}>
                  {loadingModels && <Loader2 className="mr-1 size-3 animate-spin" />}
                  获取模型列表
                </Button>
              </div>
              <Select value={form.llm_model}
                onValueChange={(v) => v && setForm({ ...form, llm_model: v })}>
                <SelectTrigger id="model" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {models.map((m) => (
                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                点击"获取模型列表"将从已保存的 Base URL 实时拉取供应商模型；若刚修改 Key/URL，请先保存。
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Button type="submit">保存</Button>
              {message && <span className="text-sm text-green-700">{message}</span>}
              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
