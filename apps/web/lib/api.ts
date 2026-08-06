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
}

export interface InterpretResult {
  text: string;
  model: string;
  as_of: string;
}

export const api = {
  latestSignals: () => req<SignalReport>("/signals/latest"),
  computeSignals: () => req<SignalReport>("/signals/compute", { method: "POST" }),
  refreshNav: () => req<RefreshResult>("/nav/refresh", { method: "POST" }),
  portfolio: () => req<Portfolio>("/portfolio"),
  trades: () => req<Trade[]>("/trades"),
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
  interpret: () => req<InterpretResult>("/interpret", { method: "POST" }),
};
