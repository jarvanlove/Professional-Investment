# Visual QA Report: signals-redesign-20260807

## Verdict

- Task: 修复左侧边栏随页面滚动问题，重设计每周信号页：突出本周交易方案卡片、统一决策卡布局、增加旧快照提示
- Release: Pass
- Reviewed viewports and states:
  - 1440×900 桌面端：每周信号页（含交易方案、基金决策）
  - 390×844 移动端：每周信号页

## P0

- 左侧边栏固定，不随主内容滚动 ✅
- 本周交易方案卡片在计算后正确展示买入/卖出/赎回费/净现金流/执行清单 ✅
- 旧版本信号快照显示黄色提示，引导用户重新计算 ✅
- 决策卡统一布局，包含操作 badge、置信度、当前/目标/差额/底仓等关键指标 ✅

## P1

- 决策卡高度一致，双栏等宽 ✅
- 卖出卡片展示预估赎回费和实收金额 ✅
- 移动端单列布局正常 ✅
- 颜色沿用已批准 `prussian-copper` 方向，红涨绿跌 ✅

## P2

- 无

## Evidence Reviewed

- Approved design sources: `docs/design/UI_CONTRACT.md`（已批准方向 `prussian-copper`）
- Browser screenshots:
  - `docs/design/screenshots/signals-desktop-1440x900.png`
  - `docs/design/screenshots/signals-mobile-390x844.png`
- Accessibility evidence: `docs/design/qa/signals-redesign-20260807-accessibility.md`

## Required Follow-up

- 无
