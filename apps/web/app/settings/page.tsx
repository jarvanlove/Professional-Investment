"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Settings } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const [form, setForm] = useState<Settings | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
              <Input id="key" type="password" value={form.llm_api_key}
                onChange={(e) => setForm({ ...form, llm_api_key: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="url">Base URL</Label>
              <Input id="url" value={form.llm_base_url}
                onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="model">模型</Label>
              <Input id="model" list="model-suggestions" value={form.llm_model}
                onChange={(e) => setForm({ ...form, llm_model: e.target.value })} />
              <datalist id="model-suggestions">
                <option value="deepseek-chat" />
                <option value="deepseek-reasoner" />
              </datalist>
            </div>
            <Button type="submit">保存</Button>
            {message && <span className="text-sm text-green-700 ml-3">{message}</span>}
            {error && <p className="text-sm text-red-600">{error}</p>}
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
