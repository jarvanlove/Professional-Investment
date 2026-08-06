# Professional-Investment

《四只基金规则化交易与动态仓位管理方案》（docs/product/）的本地执行平台：
每周信号计算（趋势评分/四道闸门/B-S 理由代码）+ 交易日志 + 持仓费用窗口。

## 快速开始

前置：Python ≥3.11 + [uv](https://docs.astral.sh/uv/)、Node ≥20 + pnpm。

### 1. 安装依赖

在**项目根目录**执行：

```bash
pnpm install        # 安装根依赖（concurrently），同时安装 apps/web 依赖
```

后端使用 uv 管理依赖，首次启动时会自动创建虚拟环境；也可以手动进入目录安装：

```bash
cd services/quant-api
uv sync
```

### 2. 启动后端（quant-api）

```bash
cd services/quant-api
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

或在**项目根目录**一键启动后端：

```bash
pnpm dev:api
```

后端运行后：http://localhost:8010/docs 可查看 API 文档。

### 3. 启动前端（web）

```bash
cd apps/web
pnpm dev
```

或在**项目根目录**一键启动前端：

```bash
pnpm dev:web
```

前端地址：http://localhost:3010

### 4. 同时启动前后端

在**项目根目录**执行：

```bash
pnpm dev            # 同时启动 quant-api(:8010) 与 web(:3010)
```

首次使用：
1. 打开 http://localhost:3010/trades —— 录入一笔 `入金`（如 **4000**，请替换为你的真实入金金额）和四只基金的初始 `买入`（份额/净值以销售平台为准）。
2. 打开 http://localhost:3010/signals —— 点"1. 更新净值"（akshare 抓取，含 589210 代理），再点"2. 计算信号"。
3. 每周五净值披露后重复第 2 步；有动作时在下一开放日 15:00 前到场外平台手动下单，随后回"交易日志"补录。

> 注意：README 和测试里曾用 **19044.07** 作为示例金额（代表"约 4000 本金 + 15000 追加"的虚构场景），它仅用于演示和黄金测试，不是你的真实资金。如果你发现系统显示 19044.07，说明本地数据库 `services/quant-api/data/investment.db` 被录入了该示例入金。请到"交易日志"删除或修改这笔 deposit，换成你的真实金额。详见 [docs/guides/用户使用手册.md](docs/guides/用户使用手册.md)。

净值抓取失败时：天天基金 App 抄净值 → `POST /api/nav/import`（或找 agent 代为录入）。

## AI 解读（可选）

信号页点「AI 解读」可把当周信号翻译成通俗中文（本周结论 / 逐只基金解释 / 风险提示）。
先在「设置」页填写 LLM 配置（默认 DeepSeek：`https://api.deepseek.com` + `deepseek-v4-pro`），
也可用 `services/quant-api/.env` 的 `DEEPSEEK_API_KEY` 兜底。AI 只解释报告，不参与计算。

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
