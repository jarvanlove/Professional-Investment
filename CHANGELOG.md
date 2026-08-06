# Changelog

All notable user-facing or release-level changes should be documented in this file.

## [0.2.0] - 2026-08-06
### 功能
- UI 去原生化：交易日志/持仓页换用 shadcn（Base UI）组件；信号页增加每周操作步骤条
- AI 信号解读：POST /api/interpret（OpenAI 兼容，默认 DeepSeek）；/settings 页可配置 API Key / Base URL / 模型
### 设计原理
- LLM 只解释信号报告已有内容（prompt 约束），输出不进任何计算与存储——规则确定性不受 AI 影响
- 设置存 app_settings 表（优先级：表 > 环境变量 > 默认），Key 不落 Git
### 注意事项
- AI 解读为无状态调用，不保存历史；LLM 故障返回 502 不影响其他功能

## [0.1.0] - 2026-08-06

### 功能
- 一期信号仪表盘 + 交易日志：quant-core 算法库（评分/凯利约束/模式/费用）、quant-api（akshare 管道 + 账本 + 信号 API）、web 四页面

### 设计原理
- 算法独立成纯函数包，为后续 agent 平台复用（docs/superpowers/specs/2026-08-05-signal-dashboard-design.md）

### 注意事项
- 一期无 Alembic（create_all）；峰值/利润率历史从首次信号快照开始累积
- P1 单基金移动止盈一期仅在批次层提示，自动判定列入二期
- S4 硬风控卖出按 PDF 9.1 不受 25% 周缓冲；资金闸门为第四道闸门

## Unreleased

### Added

- TODO

### Changed

- TODO

### Fixed

- TODO

## When To Update This File

Update this file when:

- A change is user-visible.
- A release, migration, deploy, or compatibility note should be preserved.
- A completed task changes behavior beyond internal refactoring.

Do not update this file for every small internal code edit.
