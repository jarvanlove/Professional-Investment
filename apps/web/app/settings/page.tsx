"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Settings } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Eye, EyeOff, Copy, Check, Loader2, Search, Moon, AudioLines, Sparkles, Hexagon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface Provider {
  id: string;
  name: string;
  baseUrl: string;
  icon: LucideIcon;
  color: string;
  defaults: string[];
}

const PROVIDERS: Provider[] = [
  {
    id: "deepseek", name: "DeepSeek", baseUrl: "https://api.deepseek.com",
    icon: Search, color: "text-blue-600 bg-blue-50 border-blue-200",
    defaults: ["deepseek-v4-pro", "deepseek-v4-flash"],
  },
  {
    id: "kimi", name: "Kimi", baseUrl: "https://api.moonshot.ai/v1",
    icon: Moon, color: "text-sky-600 bg-sky-50 border-sky-200",
    defaults: ["kimi-k3", "kimi-k2.7-code"],
  },
  {
    id: "kimi-coding", name: "Kimi For Coding", baseUrl: "https://api.kimi.com/coding/v1",
    icon: Moon, color: "text-indigo-600 bg-indigo-50 border-indigo-200",
    defaults: ["kimi-k2.7-code", "kimi-k3"],
  },
  {
    id: "minimax", name: "MiniMax", baseUrl: "https://api.minimax.io/v1",
    icon: AudioLines, color: "text-red-600 bg-red-50 border-red-200",
    defaults: ["MiniMax-M3", "MiniMax-M2.7"],
  },
  {
    id: "minimax-cn", name: "MiniMax 国内", baseUrl: "https://api.minimaxi.com/v1",
    icon: AudioLines, color: "text-orange-600 bg-orange-50 border-orange-200",
    defaults: ["MiniMax-M3", "MiniMax-M2.7"],
  },
  {
    id: "qwen", name: "Qwen", baseUrl: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    icon: Sparkles, color: "text-purple-600 bg-purple-50 border-purple-200",
    defaults: ["qwen3.8-max", "qwen3.7-plus"],
  },
  {
    id: "qwen-coding", name: "Qwen Code", baseUrl: "https://coding.dashscope.aliyuncs.com/v1",
    icon: Sparkles, color: "text-fuchsia-600 bg-fuchsia-50 border-fuchsia-200",
    defaults: ["qwen3-coder-plus"],
  },
  {
    id: "qwen-cn", name: "通义千问", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    icon: Sparkles, color: "text-violet-600 bg-violet-50 border-violet-200",
    defaults: ["qwen3.8-max", "qwen3.7-plus"],
  },
  {
    id: "glm", name: "GLM", baseUrl: "https://api.z.ai/api/paas/v4",
    icon: Hexagon, color: "text-emerald-600 bg-emerald-50 border-emerald-200",
    defaults: ["glm-5.2", "glm-4.7"],
  },
  {
    id: "glm-coding", name: "GLM Coding", baseUrl: "https://api.z.ai/api/coding/paas/v4",
    icon: Hexagon, color: "text-teal-600 bg-teal-50 border-teal-200",
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
  const Icon = p.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col items-center justify-center gap-1.5 rounded-xl border px-2 py-3 text-center text-xs transition-colors min-h-[5.5rem]",
        active
          ? "border-primary bg-primary/5 text-primary ring-1 ring-primary"
          : "border-input bg-background hover:bg-muted"
      )}
    >
      <span className={cn("inline-flex size-9 items-center justify-center rounded-lg border", p.color)}>
        <Icon className="size-5" />
      </span>
      <span className="leading-tight">{p.name}</span>
    </button>
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
      setForm(s);
      setModels(normalizeOptions(defaultsFor(s.llm_provider)));
    }).catch((e) => setError(String(e)));
  }, []);

  function selectProvider(id: string) {
    const p = PROVIDERS.find((x) => x.id === id);
    if (!p || !form) return;
    setModels(normalizeOptions(p.defaults));
    setForm({
      ...form,
      llm_provider: id,
      llm_base_url: p.baseUrl,
      llm_api_key: "",
      llm_model: p.defaults[0] ?? "",
    });
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
      <h1 className="text-xl font-bold">设置</h1>
      <Card className="max-w-3xl">
        <CardHeader><CardTitle className="text-base">LLM（AI 解读）</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={save} className="space-y-5">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>供应商</Label>
                <span className="text-xs text-muted-foreground">
                  如需官方 Logo，替换 public/logos/ 下的 svg 文件
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
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
                点击卡片会自动切换 Base URL、清空当前 API Key 并填充该供应商默认模型；通用版与 Coding 版使用不同的 endpoint，请搭配对应的 API Key。
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
                点击"获取模型列表"会使用上方 Base URL 和 API Key 实时拉取对应供应商的模型。
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
