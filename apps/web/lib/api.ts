import type { Portfolio, SignalReport, Trade } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export interface RefreshResult {
  results: { code: string; status: string; added: number; error?: string }[];
}

export interface Settings {
  llm_api_key: string;
  llm_base_url: string;
  llm_model: string;
  llm_provider: string;
  deepseek_api_key: string;
  kimi_api_key: string;
  minimax_api_key: string;
  qwen_api_key: string;
  glm_api_key: string;
}

export interface TradePage {
  items: Trade[];
  total: number;
  page: number;
  page_size: number;
}

export interface InterpretResult {
  text: string;
  model: string;
  as_of: string;
}

export interface ModelsResult {
  models: string[];
}

export const api = {
  latestSignals: () => req<SignalReport>("/signals/latest"),
  computeSignals: () => req<SignalReport>("/signals/compute", { method: "POST" }),
  refreshNav: () => req<RefreshResult>("/nav/refresh", { method: "POST" }),
  portfolio: () => req<Portfolio>("/portfolio"),
  trades: (params?: { fund_code?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.fund_code) q.set("fund_code", params.fund_code);
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    const qs = q.toString();
    return req<TradePage>(`/trades${qs ? `?${qs}` : ""}`);
  },
  createTrade: (t: Omit<Trade, "id">) =>
    req<Trade>("/trades", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(t),
    }),
  settings: () => req<Settings>("/settings"),
  saveSettings: (s: Partial<Settings>) =>
    req<Settings>("/settings", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(s),
    }),
  models: (base_url: string, api_key: string) =>
    req<ModelsResult>("/settings/models-preview", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ base_url, api_key }),
    }),
  interpret: () => req<InterpretResult>("/interpret", { method: "POST" }),
};
