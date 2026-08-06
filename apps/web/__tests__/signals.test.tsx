import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import SignalsPage from "../app/signals/page";

const reportPayload = {
  as_of: "2026-08-06", regime: "neutral", total_value: 19044.07,
  portfolio_dd: 0.02, peak_profit_rate: 0.011, cash_value: 15000, cash_weight: 0.79,
  weekly_unit_budget: 2, account_actions: [],
  decisions: [],
};

function mockFetch(interpretResponder: () => Response) {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/api/interpret")) return Promise.resolve(interpretResponder());
    if (url.includes("/api/signals/latest"))
      return Promise.resolve(new Response(JSON.stringify(reportPayload), { status: 200 }));
    return Promise.resolve(new Response("{}", { status: 200 }));
  }));
}

test("AI 解读成功渲染文本", async () => {
  mockFetch(() => new Response(
    JSON.stringify({ text: "本周结论：观望", model: "deepseek-chat", as_of: "2026-08-06" }),
    { status: 200 }));
  render(<SignalsPage />);
  await waitFor(() => expect(screen.getByText("AI 解读")).toBeInTheDocument());
  fireEvent.click(screen.getByText("AI 解读"));
  await waitFor(() => expect(screen.getByText(/本周结论：观望/)).toBeInTheDocument());
});

test("未配置 Key 时提示去设置页", async () => {
  mockFetch(() => new Response(
    JSON.stringify({ detail: "未配置 API Key，请到设置页填写" }), { status: 503 }));
  render(<SignalsPage />);
  await waitFor(() => expect(screen.getByText("AI 解读")).toBeInTheDocument());
  fireEvent.click(screen.getByText("AI 解读"));
  await waitFor(() => expect(screen.getByText(/未配置 API Key/)).toBeInTheDocument());
  expect(screen.getByText("前往设置页")).toBeInTheDocument();
});
