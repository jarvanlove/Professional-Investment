import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import Dashboard from "../app/page";

const portfolioPayload = {
  funds: [
    { code: "001480", name: "财通成长优选混合A", shares: 1500, nav: 1.4052,
      nav_date: "2026-08-04", value: 2107.85, weight: 0.11, lots: [] },
  ],
  account: { cash: 15000, net_contributed: 18000, holdings: { "001480": 2107.85 },
             total_value: 19044.07, peak_value: 19044.07, portfolio_dd: 0.02,
             peak_profit_rate: 0.011 },
};

function mockFetch() {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/portfolio"))
      return Promise.resolve(new Response(JSON.stringify(portfolioPayload), { status: 200 }));
    if (url.includes("/api/signals/latest"))
      return Promise.resolve(new Response("not found", { status: 404 }));
    return Promise.resolve(new Response("{}", { status: 200 }));
  }));
}

test("仪表盘渲染账户概览", async () => {
  mockFetch();
  render(<Dashboard />);
  await waitFor(() => expect(screen.getByText("账户总资产")).toBeInTheDocument());
  expect(screen.getByText(/19,044/)).toBeInTheDocument();
  expect(screen.getByText("组合回撤")).toBeInTheDocument();
});
