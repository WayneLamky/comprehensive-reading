---
name: comprehensive-reading
description: 把用户看不懂的任何文本或文件（论文、研究计划 / proposal、合同、报告、课程材料、PDF、网页、粘贴的段落）做成一份零基础也能看懂的中文交互式精读页：先建证据地图，再按读者起点分单元讲解，每个解释块带原文锚点，固定七字段讲图、七问卡片、两栏判决、自测与答疑记录，输出离线单文件 HTML。触发词：精读、看不懂、帮我读懂、读懂这个、讲解这份文件、把 X 做成能看懂的页面、做成精读页、零基础讲解、comprehensive reading、close reading、explain this paper / document to me、teach me this paper。不用于只要摘要、只要翻译全文（用 nature-reader）或只要文献检索的请求。
---

# Comprehensive Reading · 把看不懂的东西读懂

目标不是摘要，而是让一个起点很低的读者**真的看懂**一份材料，并且每句讲解都能回到原文核对。

本 skill 合并自三套方法，每条规则后标注来源：
`[tutor]` scientific-literature-tutor（证据地图、逐图七字段、JSON 规格 → 离线 HTML、校验）；
`[learning]` UiB 科研学习总纲与六篇精读页（零基础、一次一个概念、单元结构、七问卡片、两栏判决、自测 + 答疑、三层状态文件）；
`[reader]` nature-reader（原文锚点、来源格式路由、中英对照、术语账本）。

## 必须产出

1. 一份**离线单文件 HTML 精读页**（无 CDN、无外部字体、图片内嵌），由 JSON 规格经 `scripts/build_reader.py` 生成。`[tutor]`
2. 一段简短的对话交接：告诉读者从哪个单元开始、第一道检查题是什么，并邀请按图 / 按段落提问。`[tutor]` `[learning]`

生成的 HTML 中不得嵌入 API key、私人路径、Obsidian vault 路径；公开分发前不得包含许可不允许再分发的论文原图。`[tutor]`

默认中文讲解，关键英文术语第一次出现时翻译，之后保留英文。`[tutor]`

## 工作流

### (a) 读全文，建证据地图 / 论点地图 `[tutor]` `[reader]`

- 先判断来源格式（可选中文字 PDF / 扫描 PDF / HTML / DOI / 粘贴文本 / 合同或课程材料），用一句话告诉用户你的判断；按 `references/grounding-rules.md` 第 2 节抽取。`[reader]`
- 通读全部内容：标题、摘要、正文、方法、图注、补充材料、数据可用性、利益声明；有图的页面要实际看图，不凭文字推断面板含义。`[tutor]`
- 建立私有工作地图，先不写讲解：
  - 学术研究类：`question`、`hypothesis`、`samples`（真正独立的单位）、`X`、`Y`、`model`、`validation`（留出的单位、泄漏风险、指标、外部验证）、`claims`（哪张图支持哪个主张）、`limits`。`[tutor]`
  - 非研究类（合同、报告、课程材料、政策）：逐段「主张 — 依据 — 边界」，再抽出论证骨架。`[reader]`（article-anatomy 的功能标注思路）
- 材料里的说法是「主张」，不是事实；永远不要把数据构造称为验证。`[tutor]`
- 同时开始建术语账本：一个概念一个名字。`[reader]`

### (b) 判断读者起点，列前置概念，一次一个 `[learning]`

- 从用户的话或上下文判断读者基础，写进规格 `reader.starting_point`。
- 列出读懂本材料必须先有的概念，写进 `reader.prerequisites`，标明在哪个单元补。
- 零基础先讲背景再读正文；一个单元只推进一个概念；不为赶进度跳过前置知识。
- 出现新的前置缺口时插入微型基础单元，记下返回点。

### (c) 分单元写，固定字段，每块带锚点 `[learning]` `[tutor]` `[reader]`

- 单元固定结构（尤其第一单元）：为什么要关心这个问题 → 主角是谁 → 难点 → 作者 / 材料的想法 → 本课术语。每个单元有 `goal`（唯一目标）、`check`（检查题，不用术语就能答）、`terms`。`[learning]`
- 每张主图 / 每个关键证据块按固定七字段写：本图回答什么、数据怎么来、怎么读、看到了什么、作者主张什么、不能证明什么、术语；先给一句「先记一句」。`[tutor]`
- 研究类材料填**七问卡片**（研究问题、X、Y、独立样本、验证方式、能证明、不能证明）；非研究类填「主张 — 依据 — 边界」表。`[learning]`
- 写**两栏判决**：材料支持 / 材料没有证明。两栏都要写。`[learning]`
- 每个 `lesson` / `figure` / `table` / `bilingual` / `callout` / `diagram` 块都带 `anchor`（页码 / 段落 / 图注 / 条款 / 短引）；材料没说的写 `原文未说明`，不编。`[reader]`
- 需要逐句对照的关键句用 `bilingual` 块（原句 + 忠实译文 + 锚点），短引不超过一句。`[reader]`
- 审计并克制措辞：名义样本 vs 独立单位、重复类型、留出的单位、泄漏、基线、误差、正文与图注矛盾、利益关系；没建立因果或泛化时用「支持 / 一致 / 提示」。`[tutor]`
- 完整的教学规则见 `references/teaching-rules.md`。

### (d) 写 JSON 规格 → 构建离线 HTML `[tutor]`

- 读 `references/content-schema.md`，把内容写成 UTF-8 JSON 规格，不把内容硬编码进渲染器。
- 图：开放许可（如 CC BY）的原图可用 `scripts/extract_figures.py` 裁剪后嵌入，并在 `caption` 标明来源与许可；受限的图不嵌入，用 `image_note` 说明，必要时用 `diagram` 做解释性重绘并标明。`[tutor]` `[reader]`
- 构建：

```bash
python3 scripts/validate_spec.py SPEC.json
python3 scripts/build_reader.py SPEC.json OUTPUT.html
```

- 页面自带：导航栏与单元状态、进度条、明暗切换、打印、图片放大、每块「这一节不懂」按钮、每单元「我的回答 / 我的问题」本机文本框、「导出我的问题」。若作为 claude.ai Artifact 打开且有评论能力，「这一节不懂」会直接开评论框。`[learning]` `[tutor]`

### (e) 交付前核对 `[tutor]` `[reader]`

- `validate_spec.py` 零错误；警告逐条看过。
- 打开生成的 HTML，检查顶部、至少一个中间单元、判决和总结；确认无网络请求、图片可见、控件可用。
- 逐项核对：标题、作者、年份、图编号、样本数、指标数值、主张措辞与原文一致；每个锚点能定位；术语账本前后一致；`原文未说明` 的地方确实没说。
- 不隐藏弱点；不把材料的主张写成已证实的事实。

### (f) 可选：学习状态与答疑写回 `[learning]`

- 用户要长期学习多份材料时，按 `references/state-files.md` 建三层文件：总纲 / 当前状态 / 问题索引。
- 读者在页面提问（Artifact 评论，或「导出我的问题」粘贴过来）后：先从原文回答并给锚点，再把讲解写回规格的 `units[].qa`，重新构建页面；问题索引记一行摘要；明确说下一步是继续当前单元、补前置知识还是返回原问题。
- 一次只讲一个概念，读者答完检查题才推进。

## 讲解风格 `[tutor]` `[learning]`

- 从材料想解决的问题讲起，不从软件或步骤讲起。
- 用具体映射：「早期形态 X → 数周后的分化能力 Y」。
- 每张图、每个单元先一句要点，再细节。可用比喻（`analogy` 块），比喻之后回到原文。
- 邀请按图、按面板、按段落提问。
- 不隐藏弱点：理解弱点是理解材料的一部分。

## 文件

- `scripts/build_reader.py`：规格 → 离线单文件 HTML。
- `scripts/validate_spec.py`：检查结构、锚点、七字段、图片路径。
- `scripts/extract_figures.py`：按裁剪清单从页面图裁原图（需要 Pillow）。
- `references/content-schema.md`：规格字段。
- `references/teaching-rules.md`：零基础教学规则、七问 / 七字段、审计清单。
- `references/grounding-rules.md`：锚点、来源格式路由、中英对照、术语账本。
- `references/state-files.md`：三层学习状态文件模板。
- `examples/`：两个最小规格（研究类 `study_paper`、非研究类 `proposal_argument`）及其构建结果；源文本为虚构演示材料。
