import type { DcaPlan, Portfolio, SignalReport, Trade } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export interface RefreshResult {
  results: { code: string; status: string; added: number; error?: string }[];
}

export interface NavRow {
  date: string;
  nav: number;
}

export interface LiveFund {
  code: string;
  name: string;
  estimated_nav: number | null;
  change_pct: number | null;
  estimated_value: number;
  estimated_pnl: number | null;
  time: string | null;
  has_estimate: boolean;
  note?: string;
}

export interface PortfolioLive {
  as_of: string | null;
  funds: LiveFund[];
  total_estimated_value: number;
  total_estimated_pnl: number;
}

export interface NavImportResult {
  added: number;
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
  strategy_base_weights: string;
  strategy_max_sell_ratio: string;
  strategy_max_buy_ratio: string;
  strategy_buffer_pp: string;
  strategy_fee_aversion: string;
  strategy_confidence_scaling: string;
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
  importNav: (fund_code: string, rows: NavRow[]) =>
    req<NavImportResult>("/nav/import", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ fund_code, rows }),
    }),
  portfolio: () => req<Portfolio>("/portfolio"),
  portfolioLive: () => req<PortfolioLive>("/portfolio/live"),
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
  dcaPlans: () => req<DcaPlan[]>("/dca-plans"),
  createDcaPlan: (p: Omit<DcaPlan, "id">) =>
    req<DcaPlan>("/dca-plans", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(p),
    }),
  updateDcaPlan: (id: number, p: Omit<DcaPlan, "id">) =>
    req<DcaPlan>(`/dca-plans/${id}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(p),
    }),
  deleteDcaPlan: (id: number) =>
    req<{ ok: boolean }>(`/dca-plans/${id}`, { method: "DELETE" }),
  models: (base_url: string, api_key: string) =>
    req<ModelsResult>("/settings/models-preview", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ base_url, api_key }),
    }),
  interpret: () => req<InterpretResult>("/interpret", { method: "POST" }),
};
