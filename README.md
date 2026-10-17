# comprehensive-reading

把看不懂的东西读懂：一个 Claude Code / Codex skill，把论文、研究计划、合同、报告、课程材料做成**零基础也能看懂、每句都能回到原文**的中文交互式精读页（离线单文件 HTML）。

A Claude Code / Codex skill that turns any hard-to-read document (paper, proposal, contract, report, course material) into a Chinese interactive close-reading page: evidence map first, one concept per unit, every explanation anchored to the source, fixed seven-field figure walkthroughs, a seven-question card, a two-column verdict, self-checks and a Q&A log — rendered as one offline HTML file with no CDN.

## 来源与取舍 · Sources and what was kept

| 来源 | 取了什么 | 没取什么 |
|---|---|---|
| [scientific-literature-tutor](https://github.com/WayneLamky/scientific-literature-tutor) | 先建证据地图再写；每张图固定七字段；内容放 JSON 规格、`build_reader.py` 渲染离线单文件 HTML（无 CDN、无外部字体、图片内嵌）；`validate_spec.py` 校验；导航、进度、逻辑链、样本审计、自测、中英术语表；`extract_figures.py` | GPT tutor 抽屉与 `serve_reader.py` 本地代理、Obsidian 写回（它们绑定 Codex app-server；本 skill 用「导出我的问题」+ Artifact 评论替代，页面不依赖任何服务） |
| UiB 学习总纲与六篇精读页（本地 `learning/`） | 零基础先讲背景、一次只推进一个概念、不跳前置知识；每课固定结构（为什么关心 → 主角 → 难点 → 想法 → 术语）；七问卡片；两栏判决；每单元检查题 + 答疑写回；三层学习状态文件 | 具体课程内容与 claude.ai Artifact 链接 |
| nature-reader（本地 skill） | 每个解释块带原文锚点；按来源格式路由抽取；中英对照 `bilingual` 块；术语账本 | 全文逐段翻译的 `paper.md` / `source_map.json` 输出（本 skill 是精读讲解，不是全文翻译） |

## 用法 · Usage

安装（Claude Code）：

```bash
git clone https://github.com/WayneLamky/comprehensive-reading ~/.claude/skills/comprehensive-reading
```

Codex 用户放到 `~/.codex/skills/comprehensive-reading`。

然后在对话里说「帮我读懂这篇论文」「把这份合同做成能看懂的页面」「精读这个 PDF」即可。

手动构建：

```bash
python3 scripts/validate_spec.py examples/*/spec.json
python3 scripts/build_reader.py examples/study_paper/spec.json out/study.html
```

只需要 Python 3.9+ 标准库；`extract_figures.py` 额外需要 Pillow。

## 精读页包含什么 · What a page contains

1. 全貌：一句话论点、论点地图（论文为逻辑链，非论文为论证骨架）、样本审计、七问卡片或「主张 — 依据 — 边界」表。
2. 单元：唯一目标、前置概念、讲解块（每块带原文锚点和「这一节不懂」）、固定七字段的图解、原文对照、比喻、表格、本课术语、检查题、答疑记录。
3. 两栏判决：材料支持 / 材料没有证明。
4. 总结：要点、自测、术语账本、答疑索引。
5. 页面行为：导航、进度、明暗、打印、图片放大、本机笔记（localStorage）、导出我的问题、Artifact 评论（可用时）。

## 目录 · Layout

```
SKILL.md                     触发条件与工作流（每条规则标注来源）
references/content-schema.md 规格字段
references/teaching-rules.md 教学规则、七问 / 七字段、审计清单
references/grounding-rules.md 锚点、来源格式、中英对照、术语账本
references/state-files.md    三层学习状态文件模板（可选）
scripts/build_reader.py      JSON 规格 → 离线 HTML
scripts/validate_spec.py     校验
scripts/extract_figures.py   裁图（Pillow）
examples/study_paper/        研究类示例（虚构摘要 + 自绘 SVG）
examples/proposal_argument/  非研究类示例（虚构研究计划摘录）
```

示例中的源文本都是为演示规格编写的虚构材料；仓库不包含任何论文 PDF 或受版权保护的原图。

## License

MIT, see `LICENSE`.
