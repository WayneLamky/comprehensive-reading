# 精读页规格 · Content schema

渲染器 `scripts/build_reader.py` 接受一个 UTF-8 JSON 对象；规格里的相对路径相对于规格文件所在目录解析。`scripts/validate_spec.py` 按本文件检查。

本规格合并自：scientific-literature-tutor 的 `reader_spec.json`（逐图七字段、逻辑链、样本审计、验证、自测、术语表）`[tutor]`；UiB 六篇精读页的单元结构（唯一目标、检查题、答疑、七问卡片、两栏判决）`[learning]`；nature-reader 的锚点与对照规则（`anchor`、`bilingual`、术语账本）`[reader]`。

## 顶层字段

| 字段 | 必填 | 说明 | 来源 |
|---|---|---|---|
| `document` | 是 | 见下 | tutor |
| `reader` | 否 | `starting_point`（读者起点，一句话）、`prerequisites`（数组，每项 `{concept, why, where}`） | learning |
| `thesis` | 是 | 一句中文说清整份材料 | tutor |
| `argument_map` | 是 | 有序数组：`{label, en?, text, anchor}`，论文为逻辑链，非论文为论证骨架 | tutor / reader |
| `sample_audit` | 否 | `{label, value, note}` 数组，名义样本与独立单位 | tutor |
| `card` | 是 | `mode: "study"` 时需 `study` 七问；`mode: "argument"` 时需 `claims` | learning |
| `units` | 是 | 有序单元数组，见下 | learning |
| `verdict` | 否（建议） | `{supports: [...], does_not_show: [...]}`，两栏判决；每项可为字符串或 `{text, anchor}` | learning |
| `takeaways` | 否 | 字符串或 `{text, anchor}` 数组 | tutor |
| `questions` | 否 | `{q, a, anchor?}` 自测 | tutor |
| `glossary` | 是 | `{zh, en, note?}`，术语账本 | tutor / reader |
| `source_note` | 是 | 来源、版本、许可说明，显示在页脚 | tutor |
| `series` | 否 | `{label, items: [{title, href?, here?, note?}]}`，同系列材料互链 | learning |

### `document`

`title`（必填）、`subtitle`（中文副标题，若有则作为页面主标题）、`source`（作者 / 发布方）、`venue`、`year`、`identifier`（DOI 等）、`source_file`、`kind`（`paper` / `proposal` / `contract` / `report` / `course` / `other`）、`kicker`、`key`（本机笔记存储用的稳定键）。

### `card`

```json
{"mode": "study", "study": {
  "question": "…", "x": "…", "y": "…", "independent_unit": "…",
  "validation": "…", "proves": "…", "cannot_prove": "…"}}
```

每个值可以是字符串，或 `{"text": "…", "anchor": "…"}`。

```json
{"mode": "argument", "claims": [
  {"claim": "…", "evidence": "…", "boundary": "…", "anchor": "…"}]}
```

## 单元 `units[]`

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 短 ID，如 `U1`、`S2`；不能含 `-` 或空格 |
| `title_zh` | 是 | 单元标题 |
| `title_en` | 否 | |
| `goal` | 是 | 唯一目标，一句话 |
| `status` | 否 | `todo` / `ready` / `now` / `done` |
| `concept` | 否 | 本单元只推进的一个概念 |
| `prerequisites` | 否 | 字符串数组 |
| `rail_tag` | 否 | 导航栏里的小标签，如 `Figure 3` |
| `blocks` | 是 | 至少一个块，见下 |
| `terms` | 建议 | `{en, zh, note?}` 本单元术语 |
| `check` | 建议 | `{q, hint?, expected?}`；`expected` 是参考要点，折叠显示 |
| `qa` | 否 | `{n?, date?, question, answer, anchor?, summary?}`；`answer` 可为字符串或段落数组 |

## 块 `blocks[]`

所有块都有 `kind`。下列块的 `anchor` 为**必填**：`lesson`、`figure`、`table`、`bilingual`、`callout`、`diagram`。`anchor` 可以是字符串或字符串数组；材料没说时写 `原文未说明`。

| kind | 字段 |
|---|---|
| `lesson` | `heading`、`paragraphs[]` / `bullets[]` / `steps[]`（至少一种）、`anchor` |
| `figure` | `number`、`title_zh`、`title_en?`、`image?`（相对路径，嵌入为 data URI）、`image_note?`（不嵌图时说明原因）、`caption?`、`alt?`、`takeaway?`、**固定七字段**：`question`、`provenance[]`、`reading[]`、`observations[]`、`claim`、`limitation`、`glossary[]?`、以及 `callout?`、`diagram?`、`anchor` |
| `table` | `heading`、`columns[]`、`rows[][]`、`note?`、`anchor` |
| `bilingual` | `heading?`、`original`、`zh`、`note?`、`anchor` |
| `analogy` | `heading?`、`paragraphs[]` 或 `text` |
| `callout` | `heading?`、`paragraphs[]` 或 `text`、`anchor` |
| `diagram` | `text`（如 `早期图像 → 特征 → 模型 → 预测`）、`caption?`、`anchor` |
| `terms` | `heading?`、`items[]`（`{en, zh, note?}`） |

## 文本规则

- 所有文本按纯文本处理并转义；只允许两种内联标记：`**粗体**` → 加粗，`` `term` `` → 术语样式（等宽、强调色）。
- 用数组表达并列的想法，不在字符串里塞 HTML。
- 图注用自己的话概括，不整段复制受版权保护的文字。
- 图片由渲染器嵌入为 data URI，输出单文件可离线打开。
- 解释性重绘必须在标签中标明，不得与原图混淆。
- 永远写明验证时「留出的单位」；只写「留一法」而不写留的是什么，视为不完整。

## 页面行为（渲染器内置）

- 左侧导航栏显示单元与状态；滚动进度条；明 / 暗切换；打印 / PDF；图片点击放大。
- 每个块有「这一节不懂」按钮；每个检查题下有「我的回答 / 我的问题」文本框，内容只保存在本机浏览器（localStorage）。
- 「导出我的问题」把所有文本框内容整理成 Markdown 并复制到剪贴板，方便粘贴给老师（Claude / Codex / 人）。
- 若页面作为 claude.ai Artifact 打开且有评论能力，「这一节不懂」会直接打开对该块的评论框（`window.claude.use('comments')`）；没有时自动退回本机文本框。页面不依赖任何网络资源。
