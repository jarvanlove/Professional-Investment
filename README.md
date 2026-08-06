# Professional-Investment

《四只基金规则化交易与动态仓位管理方案》（docs/product/）的本地执行平台：
每周信号计算（趋势评分/四道闸门/B-S 理由代码）+ 交易日志 + 持仓费用窗口。

## 快速开始

前置：Python ≥3.11 + [uv](https://docs.astral.sh/uv/)、Node ≥20 + pnpm。

```bash
pnpm install        # 根依赖（concurrently）
pnpm dev            # 同时启动 quant-api(:8000) 与 web(:3000)
```

首次使用：
1. 打开 http://localhost:3000/trades —— 录入一笔 `入金`（如 19044.07）和四只基金的初始 `买入`（份额/净值以销售平台为准）。
2. 打开 http://localhost:3000/signals —— 点"1. 更新净值"（akshare 抓取，含 589210 代理），再点"2. 计算信号"。
3. 每周五净值披露后重复第 2 步；有动作时在下一开放日 15:00 前到场外平台手动下单，随后回"交易日志"补录。

净值抓取失败时：天天基金 App 抄净值 → `POST /api/nav/import`（或找 agent 代为录入）。

已知口径：
- 027521（广发）使用 589210 代理净值，需累计 ≥61 个净值点；在此之前信号计算返回 422 数据不足（by design）。
- 同一周内多基金买入建议的可用现金不做跨基金递减（实际被每周 2 单元预算封顶，1.1 期再收紧）。

## 测试

```bash
pnpm test   # quant-core pytest（含 PDF 算例黄金测试）+ quant-api pytest + web vitest
```

## 结构

- `packages/quant-core` —— 纯算法库（规则参数唯一来源，禁止 Web/DB 依赖）
- `services/quant-api` —— FastAPI + SQLite（`services/quant-api/data/investment.db`，不入库）
- `apps/web` —— Next.js 16 仪表盘/信号/日志/持仓
