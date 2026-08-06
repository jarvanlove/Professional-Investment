# 设计文档：UI 统一（去原生化）+ AI 信号解读员（一期半）

- 日期：2026-08-06
- 状态：已获用户批准（2026-08-06）
- 上游：一期 spec（2026-08-05-signal-dashboard-design.md）；用户追加要求：API Key 页面可配置、模型不写死
- 范围：A. UI 统一；B. AI 信号解读（DeepSeek，OpenAI 兼容接口）

## 1. 目标与成功标准

A. UI：全站不再出现原生表单/表格控件外观；交易日志录入与列表、持仓页表格统一为 shadcn 组件；信号页显性化每周操作步骤。

B. AI：信号页点「AI 解读」得到三段式中文解读（本周结论 → 逐只基金解释 → 风险提示）；未配置 Key 时给出友好提示；Key 与模型均可在页面上配置。

成功标准：
1. 交易日志/持仓页无原生 `<input>/<select>/<table>` 元素（样式统一）。
2. 信号页顶部步骤条展示 1 更新净值 → 2 计算信号 → 3 下单 → 4 补录。
3. 配置 Key 后点「AI 解读」返回解读文本并渲染；未配置时 UI 提示去设置页配置。
4. 设置页可修改并保存 llm_api_key / llm_base_url / llm_model，立即生效（无需重启）。
5. 全部测试通过；AI 输出不参与任何规则计算（quant-core 零改动）。

## 2. 设置存储与 LLM 配置

- quant-api 新增 `app_settings` 表：`key TEXT PRIMARY KEY, value TEXT`（create_all 自动建表，无 Alembic）。
- 三个键：`llm_api_key`、`llm_base_url`（默认 `https://api.deepseek.com`）、`llm_model`（默认 `deepseek-chat`）。
- 优先级：`app_settings` 表 > 环境变量（`DEEPSEEK_API_KEY` 等）> 内置默认。`.env` 仅作初始兜底。
- `services/quant-api/.gitignore` 必须包含 `.env`（当前未包含，需补上）。
- API：`GET /api/settings` → 三个键的当前值；`PUT /api/settings`（body 为键值字典，仅允许白名单键）→ 保存。本地单机应用，值明文返回。

## 3. AI 解读接口

- `POST /api/interpret`：
  1. 读最近 `weekly_signals` 快照，无则 404（提示先计算信号）。
  2. 从设置读 LLM 配置；无 api_key 则 503 `{error: "未配置 API Key"}`。
  3. 调 `{base_url}/chat/completions`（OpenAI 兼容），system prompt 固定角色：「你是规则化交易系统的解读员。只解释信号报告中已有的内容，不得给出报告之外的买卖建议。输出三段：本周结论 / 逐只基金解释 / 风险提示。用通俗中文，避免术语或先解释术语。」user 内容为 SignalReport JSON。
  4. 返回 `{text, model, as_of}`；LLM 调用异常返回 502 + 截断错误信息。
- HTTP 客户端用 `httpx`（已在 dev 依赖，需提升为运行时依赖）；超时 60s。
- 安全红线：LLM 输出只进 UI，不回写任何表、不参与计算。

## 4. 前端改动

- 新增 shadcn 组件：`input select table label`（如缺）。
- **设置页** `/settings`：三个字段表单（模型用 Input + datalist 建议 deepseek-chat / deepseek-reasoner）+ 保存按钮 + 成功提示；导航加「设置」。
- **信号页**：顶部步骤条（静态四步说明，当前无需状态追踪）；「AI 解读」按钮 + 解读卡片（loading 转圈 / 503 显示"未配置 API Key，前往设置页"链接 / 502 显示错误摘要 / 成功渲染分段文本）。
- **交易日志页**：表单控件换 shadcn Input/Select；列表换 Table；布局改网格；提交成功显示绿色提示条。
- **持仓页**：批次表格换 shadcn Table。
- 样式约束：沿用现有 Tailwind + shadcn token，不引入新色系。

## 5. 测试策略

- quant-api：settings GET/PUT 白名单与持久化；interpret 的 404/503 分支（不真调 LLM，mock httpx）；成功分支 mock 返回固定文本断言透传。
- web：信号页解读卡片三态渲染测试（mock fetch）；设置页保存流程测试（mock fetch）。
- 验证命令：`pnpm test` + `pnpm --dir apps/web build`；实机验收由用户点一次「AI 解读」完成（真实 DeepSeek 调用）。

## 6. 非目标（本期不做）

- 对话式助手 / 工具调用（二期）
- AI 输出落库与历史回看（先无状态）
- 多用户/鉴权；Key 加密存储（本地单机明文即可）
- 流式输出（一次性返回即可）
