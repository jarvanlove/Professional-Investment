# Visual QA Report: global-visual-redesign-20260807

## Verdict

- Task: 全站视觉升级：左侧边栏导航、统一页头、KPI 卡、红买绿卖语义色，将 prussian-copper 基线铺满全部页面
- Release: Pass
- Reviewed viewports and states:
  - 1440×900 桌面：仪表盘 / 每周信号 / 交易日志 / 持仓与资金 / 设置
  - 390×844 移动：同上五页

## P0

- 五个页面全部接入左侧边栏骨架，当前页高亮（主色文字 + 左侧指示条）正常。
- 统一 PageHeader（图标 + 标题 + 说明 + 操作区）在五页一致渲染。
- 买入=红、卖出=绿语义色在 DecisionCard 徽标与顶边条生效；入金=主色蓝。
- 全站主色为基线普鲁士蓝 #0B3868，权重图使用基线蓝 + 浮光铜 #B89076，无随手色。
- 移动端边栏折叠为顶部横向滚动导航，五页均可正常浏览。

## P1

- KPI 卡带图标与主色左边条；回撤 ≥6%/≥12%、峰值利润率 ≥12% 自动切换 warning/danger 色调。
- 每周信号步骤条改为连贯 chevron；模式横幅按进攻/中性/利润保护/防守分色。
- 决策卡闸门改为「通过/拦截」药丸（不单独依赖颜色，带图标与文字）。
- 交易日志方向徽标（买入红/卖出绿/入金蓝/出金灰）、金额右对齐等宽数字。
- 持仓页 KPI 条 + 权重进度条 + 赎回费窗口批次红色调行高亮。
- 交易日志下拉框显示中文标签（修复 SelectValue 原生值显示问题）。

## P2

- 金额与百分比统一 `tabular-nums`。
- 发现并已修复：生产构建期间残留 `next start` 进程导致 chunk 缺失 500，已通过清理 `.next` 重建解决。

## Evidence Reviewed

- Approved design sources: `docs/design/decisions/UI-RFC-global-visual-redesign-20260807.md`（已批准）
- Browser screenshots: `docs/design/screenshots/{dashboard,signals,trades,portfolio,settings}-{desktop,mobile}.png`（10 张，真实生产构建截取）
- Accessibility evidence: `docs/design/qa/global-visual-redesign-20260807-accessibility.md`

## Required Follow-up

- 无
