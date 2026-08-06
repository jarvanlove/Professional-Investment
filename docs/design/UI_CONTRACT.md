---
title: Product UI Contract
status: draft
updated: 2026-08-06
---

# Product UI Contract

## Design Authority

Visual sources are authoritative in this order:

1. Approved Golden Screens or approved Figma nodes.
2. Product goals, user tasks, real content, and accessibility needs.
3. Project design tokens, product components, and interaction patterns.
4. Approved Design RFCs and decisions.
5. Project UI Skill Registry.
6. Generic or third-party UI Skills, library defaults, and model preferences.

Lower-priority sources must not override higher-priority sources.

## Project Facts

- Design Authority owner: 用户（本人）
- Approved Figma sources: 无
- Approved Stitch directions: 无
- Component entrypoint: apps/web/components/ui
- Token source: docs/design/UI_VISUAL_BASELINE.json（待创建）
- Browser verification command: pnpm --dir apps/web build && pnpm --dir apps/web dev
- Screenshot location: docs/design/screenshots
- Accessibility verification command: 手动键盘 Tab 遍历 + 颜色对比检查

## Visual Direction Baseline

- Project baseline: `docs/design/UI_VISUAL_BASELINE.json`
- Shared direction registry: `<runtime-root>/00_system/registry/ui_visual_directions.json`
- Direction selection: prussian-copper（深海铜）
- Baseline approved at: 2026-08-06
- Selection note: 用户认可方案A布局 + 稳重专业视觉方向，适合投资/金融场景

The first approved U1+ direction becomes the project baseline. U1 and U2 work must retain it. A different direction requires a U3 task, an approved Design RFC, and an updated project baseline. Implement semantic tokens such as canvas, surface, text, border, action, accent, and focus state; do not add ad hoc hex values from a color chart.

## Implementation Boundaries

- Reuse approved project components and tokens before adding a new visual value.
- Do not change information architecture or visual direction during implementation.
- Do not install a UI library, icon set, font, or visual baseline without an approved Design RFC.
- Do not update a Golden Screen or screenshot baseline without explicit approval.
- Do not use a controlled visual direction without recording the user's selection note on the UI task.
- A named third-party UI Skill may propose or execute only the role recorded in `UI_SKILL_REGISTRY.yaml`.

## Required States

When relevant, cover default, hover, active, focus-visible, disabled, loading, empty, error, success, permission, long-content, and responsive states.

## Evidence

Material UI work needs fixed-viewport browser screenshots, a Visual QA report, accessibility evidence, and explicit Design Authority approval before release.
