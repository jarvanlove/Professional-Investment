# Accessibility Evidence: settings-tabs-20260807

## 检查项

| 项 | 结果 |
|---|---|
| 键盘 Tab 遍历可到达所有输入框、按钮、下拉框 | ✅ |
| 标签页切换按钮为 `<button type="button">`，可通过 Enter/Space 激活 | ✅ |
| 输入框均关联 Label（显式或隐式） | ✅ |
| 颜色对比度沿用已批准设计系统，未引入新的低对比组合 | ✅ |
| 无嵌套表单导致的辅助技术解析错误 | ✅ |
| 图片（供应商 logo）均提供 `alt` 文本 | ✅ |

## 测试方式

- 手动键盘 Tab 遍历桌面端页面。
- 通过浏览器开发者工具检查 DOM 结构无嵌套 `<form>`。
- 复用现有 `prussian-copper` 设计 token，不新增自定义颜色。

## 备注

- 当前标签页未使用 `role="tablist"` / `role="tab"` ARIA 模式；若未来需要屏幕阅读器优化，可补充 `aria-selected` 与 `role` 属性。
