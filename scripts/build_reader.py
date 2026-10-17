#!/usr/bin/env python3
"""Render a comprehensive-reading spec (JSON) into one offline, self-contained HTML page.

Usage:
    python3 scripts/build_reader.py SPEC.json OUTPUT.html

Design constraints (see references/content-schema.md):
- No CDN, no external fonts, no network requests. Images are embedded as data URIs.
- All spec text is escaped; only a tiny inline markup is allowed:
    **bold**   -> <strong>
    `term`     -> <em class="term"> (monospace, accent colour)
- Every explanatory block carries a source anchor so the reader can go back to the original.
- Optional claude.ai Artifact comment hooks are feature-detected at runtime; the page works
  without them (local notes are kept in localStorage and can be exported as Markdown).
"""

from __future__ import annotations

import base64
import html as html_lib
import json
import mimetypes
import re
import sys
from pathlib import Path

ORIGINAL_UNKNOWN = ("原文未说明", "原文未明确说明", "原文未提及", "not stated in source")

BLOCK_KINDS = ("lesson", "figure", "table", "bilingual", "analogy", "callout", "diagram", "terms")

STUDY_FIELDS = (
    ("question", "研究问题"),
    ("x", "X · 输入 / 自变量"),
    ("y", "Y · 目标 / 结果"),
    ("independent_unit", "独立样本是谁"),
    ("validation", "怎样验证"),
    ("proves", "能证明"),
    ("cannot_prove", "不能证明"),
)

STATUS_LABEL = {"todo": "待学", "ready": "已备课", "now": "进行中", "done": "已过关"}


# --------------------------------------------------------------------------- helpers

def esc(value: object) -> str:
    return html_lib.escape(str(value), quote=True)


_INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_INLINE_TERM = re.compile(r"`([^`]+?)`")


def rich(value: object) -> str:
    """Escape text, then apply the minimal inline markup."""
    text = esc(value)
    text = _INLINE_BOLD.sub(r"<strong>\1</strong>", text)
    text = _INLINE_TERM.sub(r'<em class="term">\1</em>', text)
    return text


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def text_of(item: object) -> str:
    """Accept either a plain string or {"text": ..., "anchor": ...}."""
    if isinstance(item, dict):
        return str(item.get("text", ""))
    return str(item)


def anchor_of(item: object) -> object:
    if isinstance(item, dict):
        return item.get("anchor")
    return None


def anchor_html(anchor: object, prefix: str = "原文") -> str:
    """Render one or more source anchors. '原文未说明' is rendered as an explicit gap marker."""
    if not anchor:
        return ""
    anchors = anchor if isinstance(anchor, list) else [anchor]
    parts = []
    for a in anchors:
        a = str(a).strip()
        if not a:
            continue
        if a in ORIGINAL_UNKNOWN or a.startswith("原文未"):
            parts.append(f'<span class="anchor gap">{esc(a)}</span>')
        else:
            parts.append(f'<span class="anchor"><span class="k">{esc(prefix)}</span>{esc(a)}</span>')
    return f'<div class="anchors">{"".join(parts)}</div>' if parts else ""


def ul(items: list, cls: str = "") -> str:
    attr = f' class="{cls}"' if cls else ""
    out = []
    for item in items:
        out.append(f"<li>{rich(text_of(item))}{anchor_html(anchor_of(item))}</li>")
    return f"<ul{attr}>{''.join(out)}</ul>"


def ol(items: list) -> str:
    return "<ol>" + "".join(f"<li>{rich(text_of(i))}{anchor_html(anchor_of(i))}</li>" for i in items) + "</ol>"


def paragraphs(items: object) -> str:
    if items is None:
        return ""
    if isinstance(items, str):
        items = [items]
    return "".join(f"<p>{rich(p)}</p>" for p in items)


def ask_button(target: str) -> str:
    return f'<button class="ask" type="button" data-target="{esc(target)}">这一节不懂</button>'


# --------------------------------------------------------------------------- blocks

def block_lesson(b: dict, bid: str) -> str:
    bullets = ul(b["bullets"]) if b.get("bullets") else ""
    numbered = ol(b["steps"]) if b.get("steps") else ""
    return (
        f'<section class="block lesson" id="{bid}">'
        f'<div class="block-head"><h3>{rich(b.get("heading", ""))}</h3>{ask_button(bid)}</div>'
        f'{paragraphs(b.get("paragraphs"))}{bullets}{numbered}'
        f'{anchor_html(b.get("anchor"))}</section>'
    )


def block_figure(b: dict, bid: str, base: Path) -> str:
    img = ""
    if b.get("image"):
        src = (base / b["image"]).resolve()
        alt = b.get("alt") or f'{b.get("number", "Figure")} {b.get("title_en", b.get("title_zh", ""))}'
        caption = b.get("caption") or "原图 · 点击可放大"
        img = (
            f'<figure class="fig"><div class="img-scroll"><img loading="lazy" src="{data_uri(src)}" alt="{esc(alt)}"></div>'
            f"<figcaption>{rich(caption)}</figcaption></figure>"
        )
    elif b.get("image_note"):
        img = f'<div class="img-missing"><span class="label">原图未嵌入</span><p>{rich(b["image_note"])}</p></div>'
    diagram = ""
    if b.get("diagram"):
        diagram = f'<div class="diagram" aria-label="解释性重绘"><span>解释性重绘</span>{rich(b["diagram"])}</div>'
    callout = ""
    if b.get("callout"):
        callout = f'<div class="callout"><b>最容易读错的地方</b><p>{rich(b["callout"])}</p></div>'
    glossary = ""
    if b.get("glossary"):
        glossary = '<div class="chips">' + "".join(
            f'<span class="chip"><b>{esc(t["zh"])}</b><small>{esc(t["en"])}</small></span>' for t in b["glossary"]
        ) + "</div>"
    title_en = f'<p class="en-title">{esc(b["title_en"])}</p>' if b.get("title_en") else ""
    takeaway = f'<div class="key"><span>先记一句</span><strong>{rich(b["takeaway"])}</strong></div>' if b.get("takeaway") else ""
    return (
        f'<section class="block figure" id="{bid}">'
        f'<div class="block-head"><div><p class="label">{esc(b.get("number", "FIGURE"))} · 固定七字段</p>'
        f'<h3>{rich(b.get("title_zh", ""))}</h3>{title_en}</div>{ask_button(bid)}</div>'
        f"{takeaway}{img}{diagram}"
        f'<div class="q-card"><span>1 · 本图回答什么 / Question</span><p>{rich(b["question"])}</p></div>'
        f'<div class="seven">'
        f'<details open><summary>2 · 数据怎么来 <small>Data provenance</small></summary>{ol(b["provenance"])}</details>'
        f'<details open><summary>3 · 图怎么读 <small>Reading guide</small></summary>{ul(b["reading"])}</details>'
        f'<details><summary>4 · 看到了什么 <small>Observation</small></summary>{ul(b["observations"])}</details>'
        f'<details><summary>5 · 作者主张什么 <small>Claim</small></summary><p>{rich(b["claim"])}</p></details>'
        f'<details class="limit"><summary>6 · 不能证明什么 <small>Limitation</small></summary><p>{rich(b["limitation"])}</p></details>'
        f'<details><summary>7 · 术语 <small>Glossary</small></summary>{glossary or "<p>见本单元术语。</p>"}</details>'
        f"</div>{callout}{anchor_html(b.get('anchor'), '原文 / 图注')}</section>"
    )


def block_table(b: dict, bid: str) -> str:
    head = "".join(f"<th>{rich(c)}</th>" for c in b["columns"])
    rows = "".join("<tr>" + "".join(f"<td>{rich(c)}</td>" for c in r) + "</tr>" for r in b["rows"])
    note = f'<p class="muted">{rich(b["note"])}</p>' if b.get("note") else ""
    return (
        f'<section class="block table" id="{bid}">'
        f'<div class="block-head"><h3>{rich(b.get("heading", ""))}</h3>{ask_button(bid)}</div>'
        f'<div class="tbl-scroll"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
        f"{note}{anchor_html(b.get('anchor'))}</section>"
    )


def block_bilingual(b: dict, bid: str) -> str:
    note = f'<p class="muted">{rich(b["note"])}</p>' if b.get("note") else ""
    return (
        f'<section class="block bilingual" id="{bid}">'
        f'<div class="block-head"><h3>{rich(b.get("heading", "原文对照"))}</h3>{ask_button(bid)}</div>'
        f'<div class="pair"><div class="orig"><span class="label">Original</span><p>{esc(b["original"])}</p></div>'
        f'<div class="zh"><span class="label">中文</span><p>{rich(b["zh"])}</p></div></div>'
        f"{note}{anchor_html(b.get('anchor'))}</section>"
    )


def block_analogy(b: dict, bid: str) -> str:
    return (
        f'<section class="block analogy" id="{bid}"><span class="label">{esc(b.get("heading", "打个比方"))}</span>'
        f'{paragraphs(b.get("paragraphs") or b.get("text"))}</section>'
    )


def block_callout(b: dict, bid: str) -> str:
    return (
        f'<section class="block callout-block" id="{bid}"><div class="callout"><b>{rich(b.get("heading", "注意"))}</b>'
        f'{paragraphs(b.get("paragraphs") or b.get("text"))}</div>{anchor_html(b.get("anchor"))}</section>'
    )


def block_diagram(b: dict, bid: str) -> str:
    cap = f'<p class="muted">{rich(b["caption"])}</p>' if b.get("caption") else ""
    return (
        f'<section class="block" id="{bid}"><div class="diagram" aria-label="解释性重绘"><span>解释性重绘</span>{rich(b["text"])}</div>{cap}'
        f"{anchor_html(b.get('anchor'))}</section>"
    )


def block_terms(b: dict, bid: str) -> str:
    items = "".join(
        f'<dt>{esc(t["en"])}</dt><dd>{rich(t["zh"])}{(" · " + rich(t["note"])) if t.get("note") else ""}</dd>' for t in b["items"]
    )
    return (
        f'<section class="block terms-block" id="{bid}"><div class="block-head"><h3>{rich(b.get("heading", "本课术语"))}</h3>{ask_button(bid)}</div>'
        f'<dl class="terms">{items}</dl></section>'
    )


def render_block(b: dict, bid: str, base: Path) -> str:
    kind = b.get("kind", "lesson")
    if kind == "lesson":
        return block_lesson(b, bid)
    if kind == "figure":
        return block_figure(b, bid, base)
    if kind == "table":
        return block_table(b, bid)
    if kind == "bilingual":
        return block_bilingual(b, bid)
    if kind == "analogy":
        return block_analogy(b, bid)
    if kind == "callout":
        return block_callout(b, bid)
    if kind == "diagram":
        return block_diagram(b, bid)
    if kind == "terms":
        return block_terms(b, bid)
    raise ValueError(f"unknown block kind: {kind}")


# --------------------------------------------------------------------------- units

def unit_terms(unit: dict) -> str:
    if not unit.get("terms"):
        return ""
    items = "".join(
        f'<dt>{esc(t["en"])}</dt><dd>{rich(t["zh"])}{(" · " + rich(t["note"])) if t.get("note") else ""}</dd>' for t in unit["terms"]
    )
    return f'<section class="block terms-block" id="{esc(unit["id"])}-terms"><h3>本单元术语</h3><dl class="terms">{items}</dl></section>'


def unit_check(unit: dict, qa_counter: list[int]) -> str:
    check = unit.get("check")
    qa_items = unit.get("qa") or []
    uid = unit["id"]
    if not check and not qa_items:
        return ""
    out = [f'<section class="block check-block" id="{esc(uid)}-check"><div class="check">']
    if check:
        out.append(f'<p class="label">{esc(uid)} 检查题 · 不用术语，几句话就行</p><p class="q">{rich(check["q"])}</p>')
        if check.get("hint"):
            out.append(f'<p class="muted">提示：{rich(check["hint"])}</p>')
        out.append(
            f'<div class="note-box"><label for="note-{esc(uid)}">我的回答 / 我的问题（仅保存在本机浏览器）</label>'
            f'<textarea id="note-{esc(uid)}" data-note="{esc(uid)}" rows="4" placeholder="写下你的回答，或者卡在哪里。"></textarea>'
            f'<div class="row"><button class="btn" type="button" data-target="{esc(uid)}-check">发给老师</button>'
            f'<span class="saved" data-saved="{esc(uid)}"></span></div></div>'
        )
        if check.get("expected"):
            out.append(f'<details class="expected"><summary>参考要点（先自己写完再看）</summary>{paragraphs(check["expected"])}</details>')
    for qa in qa_items:
        qa_counter[0] += 1
        n = qa.get("n", qa_counter[0])
        date = f' · {esc(qa["date"])}' if qa.get("date") else ""
        quote = f'<blockquote>{rich(qa["question"])}</blockquote>'
        ans = qa.get("answer")
        body = ul(ans) if isinstance(ans, list) and ans and not isinstance(ans[0], str) else paragraphs(ans)
        out.append(
            f'<div class="qa" id="qa-{n}"><p class="label">答疑 {n}{date}</p>{quote}{body}{anchor_html(qa.get("anchor"))}</div>'
        )
    out.append("</div></section>")
    return "".join(out)


def render_unit(unit: dict, base: Path, qa_counter: list[int]) -> str:
    uid = unit["id"]
    status = unit.get("status", "ready")
    status_label = STATUS_LABEL.get(status, status)
    goal = f'<p class="goal">唯一目标：{rich(unit["goal"])}</p>' if unit.get("goal") else ""
    concept = f'<p class="muted">本单元只推进一个概念：{rich(unit["concept"])}</p>' if unit.get("concept") else ""
    prereq = ""
    if unit.get("prerequisites"):
        prereq = '<div class="prereq"><span class="label">前置概念</span>' + ul(unit["prerequisites"]) + "</div>"
    title_en = f'<p class="en-title">{esc(unit["title_en"])}</p>' if unit.get("title_en") else ""
    blocks = "".join(render_block(b, f"{uid}-{i}", base) for i, b in enumerate(unit.get("blocks", []), 1))
    return (
        f'<div class="unit-banner" id="{esc(uid)}"><p class="status {esc(status)}">{esc(uid)} · {esc(status_label)}</p>'
        f'<h2>{rich(unit["title_zh"])}</h2>{title_en}{goal}{concept}{prereq}</div>'
        f"{blocks}{unit_terms(unit)}{unit_check(unit, qa_counter)}"
    )


# --------------------------------------------------------------------------- overview parts

def render_card(card: dict) -> str:
    mode = card.get("mode", "study")
    if mode == "study":
        study = card["study"]
        rows = "".join(
            f"<dt>{esc(label)}</dt><dd>{rich(text_of(study[key]))}{anchor_html(anchor_of(study[key]))}</dd>" for key, label in STUDY_FIELDS
        )
        return f'<div class="card7-wrap"><p class="label">七问卡片 · 每篇研究都填同一张</p><dl class="card7">{rows}</dl></div>'
    claims = card["claims"]
    rows = "".join(
        f'<tr><td>{rich(c["claim"])}</td><td>{rich(c["evidence"])}</td><td>{rich(c["boundary"])}</td><td>{anchor_html(c.get("anchor"))}</td></tr>'
        for c in claims
    )
    return (
        '<div class="card7-wrap"><p class="label">主张 — 依据 — 边界 · 非研究类文本用这张表</p>'
        f'<div class="tbl-scroll"><table class="claims"><thead><tr><th>主张</th><th>依据</th><th>边界 / 没说的</th><th>原文位置</th></tr></thead><tbody>{rows}</tbody></table></div></div>'
    )


def render_verdict(v: dict | None) -> str:
    if not v:
        return ""
    return (
        '<section class="section" id="verdict"><p class="label">两栏判决</p><h2>这份材料能说明什么，不能说明什么</h2>'
        f'<div class="verdict"><div class="box yes"><h4>材料支持</h4>{ul(v.get("supports", []))}</div>'
        f'<div class="box no"><h4>材料没有证明</h4>{ul(v.get("does_not_show", []))}</div></div></section>'
    )


# --------------------------------------------------------------------------- page

CSS = r"""
:root{--bg:#f4f6f5;--surface:#fff;--fg:#1c2321;--muted:#58645f;--line:#d6dedb;--accent:#b3315f;--accent-soft:#f8e4ec;--qa:#e6f1ee;--qa-line:#2c7a69;--warn:#8a5b00;--warn-soft:#fff3d6;--no:#a8392c;--yes:#2c7a69;
--font-display:"Songti SC","STSong","Noto Serif SC",Georgia,serif;--font-body:"PingFang SC","Hiragino Sans GB","Noto Sans SC","Microsoft YaHei",system-ui,sans-serif;--font-mono:ui-monospace,"SF Mono",Menlo,"Noto Sans Mono",monospace}
body.dark{--bg:#111614;--surface:#18201d;--fg:#e4ebe8;--muted:#97a5a0;--line:#2b3532;--accent:#e4769e;--accent-soft:#3a1d29;--qa:#14302a;--qa-line:#5cc4aa;--warn:#e3a25c;--warn-soft:#2d2410;--no:#e0796b;--yes:#5cc4aa;color-scheme:dark}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--font-body);font-size:1rem;line-height:1.8}
h1,h2,h3,h4{font-family:var(--font-display);line-height:1.35;margin:0;text-wrap:balance}h1{font-size:2.1rem}h2{font-size:1.5rem}h3{font-size:1.15rem}h4{font-size:1.05rem}
p{margin:0}p+p,ul+p,p+ul{margin-top:.7em}ul,ol{margin:.5em 0 0;padding-left:1.4em}li+li{margin-top:.35em}a{color:var(--accent)}
.label{font-family:var(--font-mono);font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:0 0 .35em}.muted{color:var(--muted);font-size:.93rem;margin-top:.6em}
em.term{font-style:normal;font-family:var(--font-mono);font-size:.9em;color:var(--accent)}.mono{font-family:var(--font-mono)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
#progress{position:fixed;z-index:30;top:0;left:0;height:4px;width:0;background:var(--accent)}
.topbar{position:fixed;z-index:20;top:14px;right:16px;display:flex;gap:8px}.topbar button{border:1px solid var(--line);background:var(--surface);color:var(--fg);border-radius:999px;padding:7px 12px;cursor:pointer;font:inherit;font-size:.85rem}
.wrap{max-width:1100px;margin:0 auto;padding:32px 16px 80px;display:grid;grid-template-columns:230px minmax(0,1fr);gap:44px}
.rail{position:sticky;top:24px;align-self:start;display:flex;flex-direction:column;gap:22px;max-height:calc(100vh - 48px);overflow:auto}.rail ol{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:2px}
.rail li{display:grid;grid-template-columns:2.8em 1fr;gap:6px;padding:6px 8px;border-radius:6px;font-size:.88rem;line-height:1.45;color:var(--muted)}.rail li .n{font-family:var(--font-mono);font-size:.8rem}.rail li a{color:inherit;text-decoration:none}.rail li.active{background:var(--surface);color:var(--fg);box-shadow:0 1px 4px rgba(0,0,0,.06)}
.rail li.done{color:var(--yes)}.rail li.now{color:var(--accent);font-weight:600}.rail .tag{display:block;font-size:.75rem;opacity:.8}
main{min-width:0}
header.top{margin-bottom:28px}header.top .meta{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--muted);font-size:.9rem;margin-top:10px}header.top .thesis{margin-top:20px;border-left:4px solid var(--accent);padding:6px 0 6px 16px;font-size:1.12rem;font-weight:600}
.starting{margin-top:18px;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 18px}
.section{margin:38px 0}
.argmap{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:14px}.argmap article{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px}.argmap article>span{font-family:var(--font-mono);color:var(--accent);font-weight:700}.argmap small{color:var(--muted);display:block}.argmap p{margin-top:6px;font-size:.95rem}
.audit{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-top:14px}.audit div{background:var(--fg);color:var(--bg);border-radius:12px;padding:14px}.audit span{font-size:.78rem;opacity:.8}.audit b{display:block;font-size:1.4rem;color:var(--accent-soft)}.audit p{font-size:.85rem;margin-top:4px;opacity:.9}
.card7-wrap{margin-top:16px}.card7{display:grid;grid-template-columns:9em 1fr;gap:8px 14px;margin:0;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px 18px}.card7 dt{font-weight:700;color:var(--accent)}.card7 dd{margin:0}
.tbl-scroll{overflow:auto;margin-top:10px}table{width:100%;border-collapse:collapse;background:var(--surface);font-size:.93rem}th,td{text-align:left;padding:9px 11px;border-bottom:1px solid var(--line);vertical-align:top}th{background:var(--accent-soft);color:var(--fg);font-weight:700}
.unit-banner{margin:56px 0 18px;padding-top:26px;border-top:2px solid var(--accent)}.status{font-family:var(--font-mono);font-size:.8rem;color:var(--muted);margin-bottom:6px}.status.done{color:var(--yes)}.status.now{color:var(--accent)}.goal{margin-top:10px;font-weight:600}.en-title{color:var(--muted);font-style:italic;font-size:.95rem;margin-top:4px}
.prereq{margin-top:12px;background:var(--warn-soft);border-radius:10px;padding:10px 14px;font-size:.93rem}.prereq .label{color:var(--warn)}
.block{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:14px 0}.block-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px}.block-head h3{margin:0}
.ask{flex:none;border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:999px;padding:4px 10px;font:inherit;font-size:.78rem;cursor:pointer}.ask:hover{color:var(--accent);border-color:var(--accent)}
.anchors{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}.anchor{font-family:var(--font-mono);font-size:.76rem;color:var(--muted);background:var(--bg);border:1px dashed var(--line);border-radius:6px;padding:2px 8px}.anchor .k{color:var(--accent);margin-right:6px}.anchor.gap{border-style:solid;border-color:var(--warn);color:var(--warn)}
.fig{margin:14px 0}.img-scroll{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:10px;padding:8px}.img-scroll img{display:block;max-width:100%;max-height:900px;object-fit:contain;margin:0 auto;cursor:zoom-in}figcaption{color:var(--muted);font-size:.88rem;margin-top:8px}
.img-missing{border:1px dashed var(--warn);border-radius:10px;padding:10px 14px;margin:12px 0;font-size:.92rem}.img-missing .label{color:var(--warn)}
.key{display:grid;grid-template-columns:6em 1fr;gap:12px;background:var(--accent);color:#fff;border-radius:12px;padding:12px 16px;margin:10px 0 14px}.key span{font-weight:700;opacity:.9}
.q-card{border-left:4px solid var(--warn);background:var(--warn-soft);padding:12px 16px;border-radius:0 10px 10px 0;margin:12px 0}.q-card span{font-weight:700;color:var(--warn);font-size:.85rem}.q-card p{font-size:1.05rem;margin-top:2px}
.seven{display:grid;grid-template-columns:1fr 1fr;gap:10px}details{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:0 14px}summary{cursor:pointer;font-weight:700;padding:11px 0}summary small{color:var(--muted);font-weight:500;margin-left:6px}details>*:not(summary){margin-bottom:10px}details.limit{border-color:var(--no)}details.expected{margin-top:10px}
.diagram{display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap;margin:12px 0;padding:14px;border:1px dashed var(--accent);border-radius:12px;font-family:var(--font-mono);font-weight:700;font-size:.95rem}.diagram span{background:var(--accent);color:#fff;border-radius:999px;padding:2px 10px;font-size:.72rem;font-weight:500}
.callout{background:var(--accent-soft);border:1px solid var(--accent);border-radius:12px;padding:12px 16px;margin-top:12px}.callout b{color:var(--accent)}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{display:inline-flex;gap:6px;align-items:baseline;background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:.88rem}.chip small{color:var(--muted)}
.analogy{background:var(--qa);border-color:var(--qa-line)}.analogy .label{color:var(--qa-line)}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}.pair .orig p{font-family:Georgia,"Times New Roman",serif;font-size:.95rem}.pair .label{color:var(--accent)}
dl.terms{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;margin:8px 0 0}dl.terms dt{font-family:var(--font-mono);font-size:.88rem;color:var(--accent)}dl.terms dd{margin:0;font-size:.95rem}
.check{border:2px solid var(--accent);border-radius:12px;padding:14px 18px}.check .q{font-size:1.08rem;font-weight:600;margin-top:4px}.note-box{margin-top:12px}.note-box label{display:block;font-size:.85rem;color:var(--muted);margin-bottom:4px}.note-box textarea{width:100%;font:inherit;font-size:.95rem;border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--bg);color:var(--fg);resize:vertical}.note-box .row{display:flex;gap:12px;align-items:center;margin-top:6px}.saved{font-size:.8rem;color:var(--muted)}
.btn{border:1px solid var(--accent);background:var(--accent);color:#fff;border-radius:999px;padding:6px 14px;font:inherit;font-size:.88rem;cursor:pointer}.btn.ghost{background:transparent;color:var(--accent)}
.qa{margin-top:16px;background:var(--qa);border-left:4px solid var(--qa-line);border-radius:0 10px 10px 0;padding:12px 16px}.qa .label{color:var(--qa-line)}.qa blockquote{margin:6px 0 10px;padding-left:12px;border-left:2px solid var(--qa-line);color:var(--muted);font-style:italic}
.verdict{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}.verdict .box{border-radius:12px;padding:14px 18px;border:2px solid}.verdict .yes{border-color:var(--yes)}.verdict .yes h4{color:var(--yes)}.verdict .no{border-color:var(--no)}.verdict .no h4{color:var(--no)}
.takeaways{list-style:none;padding:0;margin-top:12px}.takeaways li{display:grid;grid-template-columns:2.4em 1fr;gap:10px;padding:10px 0;border-bottom:1px solid var(--line)}.takeaways span{font-family:var(--font-mono);color:var(--accent);font-weight:700}
.quiz{margin:8px 0;background:var(--surface)}
.qa-log{margin-top:8px}.export-box{margin-top:14px}.export-box textarea{width:100%;font-family:var(--font-mono);font-size:.82rem;border:1px solid var(--line);border-radius:8px;padding:8px;background:var(--bg);color:var(--fg);min-height:120px}
footer{margin-top:40px;color:var(--muted);font-size:.86rem;border-top:1px solid var(--line);padding-top:14px}
.modal{display:none;position:fixed;z-index:50;inset:0;background:rgba(0,0,0,.88);padding:20px;align-items:center;justify-content:center}.modal.open{display:flex}.modal img{max-width:96vw;max-height:94vh;object-fit:contain}.modal button{position:absolute;right:20px;top:16px;background:#fff;border:0;border-radius:999px;padding:8px 12px;cursor:pointer}
.series{font-size:.88rem}.series li{display:flex;justify-content:space-between;gap:8px}.series .here{font-weight:700;color:var(--accent)}
@media(max-width:900px){.wrap{display:block}.rail{position:static;max-height:none;margin-bottom:24px}.seven,.pair,.verdict{grid-template-columns:1fr}.card7{grid-template-columns:1fr}.card7 dt{margin-top:8px}.topbar{top:8px;right:8px}}
@media print{.topbar,#progress,.ask,.note-box,.rail .tag{display:none!important}.wrap{display:block}details>*{display:block!important}.block{break-inside:avoid}}
"""

JS = r"""
(function(){
  var progress=document.getElementById('progress');
  function update(){var h=document.documentElement;var p=h.scrollTop/(h.scrollHeight-h.clientHeight)*100;progress.style.width=Math.max(0,p||0)+'%';}
  addEventListener('scroll',update,{passive:true});update();
  var themeBtn=document.getElementById('theme');
  function applyTheme(t){document.body.classList.toggle('dark',t==='dark');}
  try{applyTheme(localStorage.getItem('cr-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));}catch(e){}
  themeBtn.onclick=function(){var d=!document.body.classList.contains('dark');applyTheme(d?'dark':'light');try{localStorage.setItem('cr-theme',d?'dark':'light');}catch(e){}};
  document.getElementById('print').onclick=function(){window.print();};
  var modal=document.getElementById('modal'),modalImg=modal.querySelector('img');
  document.querySelectorAll('.img-scroll img').forEach(function(img){img.onclick=function(){modalImg.src=img.src;modal.classList.add('open');};});
  modal.onclick=function(e){if(e.target!==modalImg)modal.classList.remove('open');};
  addEventListener('keydown',function(e){if(e.key==='Escape')modal.classList.remove('open');});
  var links=[].slice.call(document.querySelectorAll('.rail a[href^="#"]'));
  var targets=links.map(function(a){return document.querySelector(a.getAttribute('href'));}).filter(Boolean);
  if('IntersectionObserver' in window){var spy=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){links.forEach(function(a){a.parentElement.parentElement.classList.toggle('active',a.getAttribute('href')==='#'+e.target.id);});}});},{rootMargin:'-15% 0px -75%'});targets.forEach(function(t){spy.observe(t);});}
  var KEY='cr-notes:'+(document.body.getAttribute('data-doc-key')||location.pathname);
  var notes={};try{notes=JSON.parse(localStorage.getItem(KEY)||'{}');}catch(e){notes={};}
  document.querySelectorAll('textarea[data-note]').forEach(function(ta){var id=ta.getAttribute('data-note');if(notes[id])ta.value=notes[id];var saved=document.querySelector('[data-saved="'+id+'"]');var t=null;ta.addEventListener('input',function(){clearTimeout(t);t=setTimeout(function(){notes[id]=ta.value;try{localStorage.setItem(KEY,JSON.stringify(notes));if(saved)saved.textContent='已保存到本机 '+new Date().toLocaleTimeString();}catch(e){if(saved)saved.textContent='浏览器不允许保存，请复制到别处';}},300);});});
  var comments=null;
  function openComposer(el){if(comments){comments.openComposer({element:el}).catch(function(){focusNote(el);});}else{focusNote(el);}}
  function focusNote(el){var unit=el.id.split('-')[0];var ta=document.getElementById('note-'+unit)||document.querySelector('textarea[data-note]');if(ta){ta.scrollIntoView({behavior:'smooth',block:'center'});ta.focus();if(!ta.value)ta.value='关于「'+(el.querySelector('h3,h2,.q')||el).textContent.trim().slice(0,40)+'」：';}}
  document.querySelectorAll('[data-target]').forEach(function(btn){btn.addEventListener('click',function(){var el=document.getElementById(btn.getAttribute('data-target'));if(el)openComposer(el);});});
  if(window.claude&&typeof window.claude.use==='function'){try{window.claude.use('comments').then(function(c){if(c)comments=c;},function(){});}catch(e){}}
  var exportBtn=document.getElementById('export');var exportBox=document.getElementById('export-box');
  if(exportBtn){exportBtn.onclick=function(){var lines=['# 我的问题 · '+document.title,''];document.querySelectorAll('textarea[data-note]').forEach(function(ta){if(ta.value.trim()){var unit=ta.getAttribute('data-note');var h=document.getElementById(unit);lines.push('## '+unit+(h?' · '+h.querySelector('h2').textContent.trim():''));lines.push('');lines.push(ta.value.trim());lines.push('');}});var text=lines.join('\n');exportBox.value=text;exportBox.parentElement.hidden=false;if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(function(){exportBtn.textContent='已复制，可直接粘贴给老师';},function(){});}};}
})();
"""


def build(data: dict, spec_path: Path) -> str:
    doc = data["document"]
    base = spec_path.parent
    kicker = doc.get("kicker") or f'{doc.get("kind", "document").upper()} · 精读'
    meta_parts = [doc.get("source"), doc.get("venue"), doc.get("year"), doc.get("identifier"), doc.get("source_file")]
    meta = "".join(f"<span>{esc(m)}</span>" for m in meta_parts if m)

    reader = data.get("reader") or {}
    starting = ""
    if reader.get("starting_point") or reader.get("prerequisites"):
        pre = ""
        if reader.get("prerequisites"):
            pre = '<p class="label" style="margin-top:10px">先补这些前置概念，一次一个</p>' + ol(
                [
                    (f'{p["concept"]}：{p.get("why", "")}' + (f'（在 {p["where"]} 讲）' if p.get("where") else "")) if isinstance(p, dict) else p
                    for p in reader["prerequisites"]
                ]
            )
        starting = (
            f'<div class="starting"><p class="label">读者起点</p><p>{rich(reader.get("starting_point", ""))}</p>{pre}</div>'
        )

    argmap = "".join(
        f'<article><span>{i:02d}</span><h3>{rich(s["label"])}</h3>{("<small>" + esc(s["en"]) + "</small>") if s.get("en") else ""}<p>{rich(s["text"])}</p>{anchor_html(s.get("anchor"))}</article>'
        for i, s in enumerate(data["argument_map"], 1)
    )
    audit = ""
    if data.get("sample_audit"):
        audit = '<div class="audit">' + "".join(
            f'<div><span>{esc(a["label"])}</span><b>{esc(a["value"])}</b><p>{rich(a.get("note", ""))}</p></div>' for a in data["sample_audit"]
        ) + "</div>"

    qa_counter = [0]
    units_html = "".join(render_unit(u, base, qa_counter) for u in data["units"])

    rail_units = "".join(
        f'<li class="{esc(u.get("status", "ready"))}"><span class="n">{esc(u["id"])}</span><span><a href="#{esc(u["id"])}">{esc(u["title_zh"])}</a>'
        f'<span class="tag">{esc(STATUS_LABEL.get(u.get("status", "ready"), u.get("status", "")))}{(" · " + esc(u["rail_tag"])) if u.get("rail_tag") else ""}</span></span></li>'
        for u in data["units"]
    )
    series = ""
    if data.get("series"):
        s = data["series"]
        items = []
        for it in s.get("items", []):
            if it.get("href") and not it.get("here"):
                title = f'<a href="{esc(it["href"])}">{esc(it["title"])}</a>'
            else:
                title = esc(it["title"])
            note = it.get("note", "本页" if it.get("here") else "")
            cls = "here" if it.get("here") else ""
            items.append(f'<li class="{cls}"><span>{title}</span><span class="st">{esc(note)}</span></li>')
        series = f'<nav class="series"><p class="label">{esc(s.get("label", "系列"))}</p><ol>{"".join(items)}</ol></nav>'

    takeaways = ""
    if data.get("takeaways"):
        takeaways = '<h3>读完以后应该会什么</h3><ol class="takeaways">' + "".join(
            f'<li><span>{i:02d}</span><div>{rich(text_of(t))}{anchor_html(anchor_of(t))}</div></li>' for i, t in enumerate(data["takeaways"], 1)
        ) + "</ol>"
    questions = ""
    if data.get("questions"):
        questions = '<h3 style="margin-top:22px">自测</h3>' + "".join(
            f'<details class="quiz"><summary>{rich(q["q"])}</summary><p>{rich(q["a"])}</p>{anchor_html(q.get("anchor"))}</details>' for q in data["questions"]
        )
    glossary = "".join(
        f'<tr><td>{esc(g["zh"])}</td><td>{esc(g["en"])}</td><td>{rich(g.get("note", ""))}</td></tr>' for g in data["glossary"]
    )
    qa_log_items = []
    n = 0
    for u in data["units"]:
        for qa in u.get("qa") or []:
            n += 1
            num = qa.get("n", n)
            qa_log_items.append(f'<li><a href="#qa-{num}">答疑 {num}</a> · {esc(u["id"])}：{rich(qa.get("summary") or qa["question"])}</li>')
    qa_log = f'<h3 style="margin-top:22px">答疑记录</h3><ol class="qa-log">{"".join(qa_log_items)}</ol>' if qa_log_items else ""

    doc_key = doc.get("key") or re.sub(r"[^A-Za-z0-9_-]+", "-", str(doc.get("identifier") or doc["title"]))[:60]
    source_note = data.get("source_note", "")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(doc['title'])} · 精读</title>
<style>{CSS}</style>
</head>
<body data-doc-key="{esc(doc_key)}">
<div id="progress"></div>
<div class="topbar"><button id="theme" type="button" aria-label="切换明暗">明 / 暗</button><button id="print" type="button">打印 / PDF</button></div>
<div class="wrap">
<aside class="rail" aria-label="阅读路线">
  <nav><p class="label">阅读路线</p><ol>
    <li><span class="n">00</span><span><a href="#overview">全貌</a><span class="tag">论点地图 · 卡片</span></span></li>
    {rail_units}
    {'<li><span class="n">✓</span><span><a href="#verdict">判决</a><span class="tag">支持 / 没证明</span></span></li>' if data.get('verdict') else ''}
    <li><span class="n">▣</span><span><a href="#closing">总结</a><span class="tag">自测 · 术语 · 答疑</span></span></li>
  </ol></nav>
  {series}
  <div><button class="btn ghost" id="export" type="button">导出我的问题</button></div>
</aside>
<main>
  <header class="top">
    <p class="label">{esc(kicker)}</p>
    <h1>{rich(doc.get('subtitle') or doc['title'])}</h1>
    {('<p class="en-title">' + esc(doc['title']) + '</p>') if doc.get('subtitle') else ''}
    <div class="meta">{meta}</div>
    <div class="thesis">{rich(data['thesis'])}</div>
    {starting}
  </header>
  <section class="section" id="overview">
    <p class="label">先搭骨架 · 论点地图</p><h2>这份材料在说什么</h2>
    <div class="argmap">{argmap}</div>
    {audit}
    {render_card(data['card'])}
  </section>
  {units_html}
  {render_verdict(data.get('verdict'))}
  <section class="section" id="closing">
    <p class="label">总结</p><h2>读完以后</h2>
    {takeaways}
    {questions}
    <h3 style="margin-top:22px">术语账本 · 中英对照</h3>
    <div class="tbl-scroll"><table><thead><tr><th>中文</th><th>English</th><th>在本材料中的意思</th></tr></thead><tbody>{glossary}</tbody></table></div>
    {qa_log}
    <div class="export-box" hidden><p class="label">我的问题（已复制，可粘贴给老师）</p><textarea id="export-box" readonly></textarea></div>
    <footer>{rich(source_note)}</footer>
  </section>
</main>
</div>
<div class="modal" id="modal"><button type="button" aria-label="关闭">关闭 ×</button><img alt="放大后的图"></div>
<script>{JS}</script>
</body>
</html>"""


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: build_reader.py SPEC.json OUTPUT.html", file=sys.stderr)
        return 2
    spec = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    data = json.loads(spec.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build(data, spec), encoding="utf-8")
    print(f"Built {output} ({output.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
