"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Settings } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Eye, EyeOff, Copy, Check } from "lucide-react";

const MODELS = [
  { value: "deepseek-v4-pro", label: "deepseek-v4-pro（最新推荐）" },
  { value: "deepseek-v4-flash", label: "deepseek-v4-flash（更快更便宜）" },
];

export default function SettingsPage() {
  const [form, setForm] = useState<Settings | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.settings().then(setForm).catch((e) => setError(String(e)));
  }, []);

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

  if (error && !form) return <main className="p-8 text-red-600">加载失败：{error}</main>;
  if (!form) return <main className="p-8">加载中…</main>;

  return (
    <main className="p-8 space-y-6">
      <h1 className="text-xl font-bold">设置</h1>
      <Card className="max-w-xl">
        <CardHeader><CardTitle className="text-base">LLM（AI 解读）</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={save} className="space-y-4">
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
              <Label htmlFor="url">Base URL</Label>
              <Input id="url" value={form.llm_base_url}
                onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="model">模型</Label>
              <Select value={form.llm_model}
                onValueChange={(v) => v && setForm({ ...form, llm_model: v })}>
                <SelectTrigger id="model" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {MODELS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
