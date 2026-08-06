# Changelog

All notable user-facing or release-level changes should be documented in this file.

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
