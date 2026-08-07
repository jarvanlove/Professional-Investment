# Visual QA Report: settings-tabs-20260807

## Verdict

- Task: 将设置页拆分为模型配置/量化参数配置两个标签页，修复嵌套表单导致的 hydration 报错，并优化定投计划表单布局
- Release: Pass
- Reviewed viewports and states:
  - 1440×900 桌面端：模型配置 / 量化参数配置
  - 390×844 移动端：模型配置 / 量化参数配置

## P0

- 模型配置标签页正常显示供应商卡片、端点、API Key、模型选择 ✅
- 量化参数配置标签页正常显示底仓权重、策略参数、定投计划列表与添加表单 ✅
- 页面无嵌套 `<form>` 导致的 hydration 报错 ✅

## P1

- 切换标签页后状态保持，未触发未保存表单提交 ✅
- 保存按钮分别位于两个标签页底部，文案区分清晰 ✅
- 定投计划“添加”按钮使用 `type="button"`，不会提交外部表单 ✅
- 宽屏双栏布局正常，移动端单列布局正常 ✅

## P2

- 无

## Evidence Reviewed

- Approved design sources: `docs/design/UI_CONTRACT.md`（已批准方向 `prussian-copper`）
- Browser screenshots:
  - `docs/design/screenshots/settings-tabs-desktop-1440x900.png`
  - `docs/design/screenshots/settings-tabs-quant-desktop-1440x900.png`
  - `docs/design/screenshots/settings-tabs-mobile-390x844.png`
  - `docs/design/screenshots/settings-tabs-quant-mobile-390x844.png`
- Accessibility evidence: `docs/design/qa/settings-tabs-20260807-accessibility.md`

## Required Follow-up

- 无
