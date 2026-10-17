#!/usr/bin/env python3
"""Validate one or more comprehensive-reading specs.

Usage:
    python3 scripts/validate_spec.py SPEC.json [SPEC2.json ...]

Exit code 0 when every spec passes (warnings allowed), 1 when any spec has errors.

What is checked (see references/content-schema.md):
- required top-level fields: document.title, thesis, argument_map, card, units, glossary, source_note
- card.mode is "study" (seven fixed questions) or "argument" (claim / evidence / boundary rows)
- every unit has a unique id, title_zh, goal, and at least one block
- every explanatory block (lesson, figure, table, bilingual, callout, diagram) carries a non-empty `anchor`
  ("原文未说明" is accepted as an explicit, visible gap marker)
- figure blocks have the seven fixed fields; referenced images exist on disk
- glossary entries have zh + en; qa entries have question + answer
Warnings: units without a check question, figure blocks with neither image nor image_note,
unknown status values, units with no terms.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOP_REQUIRED = ("document", "thesis", "argument_map", "card", "units", "glossary", "source_note")
BLOCK_KINDS = {"lesson", "figure", "table", "bilingual", "analogy", "callout", "diagram", "terms"}
ANCHORED_KINDS = {"lesson", "figure", "table", "bilingual", "callout", "diagram"}
FIGURE_REQUIRED = ("number", "title_zh", "question", "provenance", "reading", "observations", "claim", "limitation")
STUDY_FIELDS = ("question", "x", "y", "independent_unit", "validation", "proves", "cannot_prove")
STATUS = {"todo", "ready", "now", "done"}


def empty(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}


def has_anchor(block: dict) -> bool:
    anchor = block.get("anchor")
    if isinstance(anchor, list):
        return any(str(a).strip() for a in anchor)
    return bool(anchor and str(anchor).strip())


def text_ok(value: object) -> bool:
    if isinstance(value, dict):
        return not empty(value.get("text"))
    return not empty(value)


def validate(path: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    stats = {"units": 0, "blocks": 0, "figures": 0, "anchors": 0, "qa": 0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"cannot parse JSON: {exc}"], warnings, stats
    if not isinstance(data, dict):
        return ["top level must be a JSON object"], warnings, stats

    for key in TOP_REQUIRED:
        if empty(data.get(key)):
            errors.append(f"missing or empty top-level field: {key}")

    doc = data.get("document") or {}
    if empty(doc.get("title")):
        errors.append("document.title is required")

    for i, step in enumerate(data.get("argument_map") or [], 1):
        if not isinstance(step, dict) or empty(step.get("label")) or empty(step.get("text")):
            errors.append(f"argument_map[{i}]: needs label and text")
        elif not has_anchor(step):
            warnings.append(f"argument_map[{i}] ({step.get('label')}): no anchor")

    card = data.get("card") or {}
    mode = card.get("mode")
    if mode == "study":
        study = card.get("study") or {}
        for key in STUDY_FIELDS:
            if not text_ok(study.get(key)):
                errors.append(f"card.study.{key} is required in study mode")
    elif mode == "argument":
        claims = card.get("claims") or []
        if not claims:
            errors.append("card.claims must have at least one row in argument mode")
        for i, c in enumerate(claims, 1):
            for key in ("claim", "evidence", "boundary"):
                if empty(c.get(key)):
                    errors.append(f"card.claims[{i}]: missing {key}")
            if not has_anchor(c):
                errors.append(f"card.claims[{i}]: missing anchor")
    else:
        errors.append('card.mode must be "study" or "argument"')

    seen_ids: set[str] = set()
    for ui, unit in enumerate(data.get("units") or [], 1):
        stats["units"] += 1
        uid = unit.get("id") or f"<unit {ui}>"
        if empty(unit.get("id")):
            errors.append(f"unit {ui}: missing id")
        elif uid in seen_ids:
            errors.append(f"duplicate unit id: {uid}")
        elif "-" in uid or " " in uid:
            errors.append(f"unit id must not contain '-' or spaces (used for element ids): {uid}")
        seen_ids.add(uid)
        if empty(unit.get("title_zh")):
            errors.append(f"{uid}: missing title_zh")
        if empty(unit.get("goal")):
            errors.append(f"{uid}: missing goal (唯一目标)")
        if unit.get("status") and unit["status"] not in STATUS:
            warnings.append(f"{uid}: unknown status '{unit['status']}' (expected one of {sorted(STATUS)})")
        blocks = unit.get("blocks") or []
        if not blocks:
            errors.append(f"{uid}: needs at least one block")
        for bi, b in enumerate(blocks, 1):
            stats["blocks"] += 1
            kind = b.get("kind", "lesson")
            label = f"{uid} block {bi} ({kind})"
            if kind not in BLOCK_KINDS:
                errors.append(f"{label}: unknown kind")
                continue
            if kind in ANCHORED_KINDS:
                if has_anchor(b):
                    stats["anchors"] += 1
                else:
                    errors.append(f"{label}: missing anchor (use '原文未说明' if the source really does not say)")
            if kind == "lesson" and empty(b.get("paragraphs")) and empty(b.get("bullets")) and empty(b.get("steps")):
                errors.append(f"{label}: lesson needs paragraphs, bullets or steps")
            if kind == "figure":
                stats["figures"] += 1
                for key in FIGURE_REQUIRED:
                    if empty(b.get(key)):
                        errors.append(f"{label}: missing {key}")
                if b.get("image"):
                    if not (path.parent / b["image"]).exists():
                        errors.append(f"{label}: image not found: {b['image']}")
                elif empty(b.get("image_note")):
                    warnings.append(f"{label}: no image and no image_note (say why the figure is not embedded)")
            if kind == "table" and (empty(b.get("columns")) or empty(b.get("rows"))):
                errors.append(f"{label}: table needs columns and rows")
            if kind == "bilingual" and (empty(b.get("original")) or empty(b.get("zh"))):
                errors.append(f"{label}: bilingual needs original and zh")
            if kind == "analogy" and empty(b.get("paragraphs")) and empty(b.get("text")):
                errors.append(f"{label}: analogy needs text")
            if kind == "callout" and empty(b.get("paragraphs")) and empty(b.get("text")):
                errors.append(f"{label}: callout needs text")
            if kind == "diagram" and empty(b.get("text")):
                errors.append(f"{label}: diagram needs text")
            if kind == "terms" and empty(b.get("items")):
                errors.append(f"{label}: terms needs items")
        if not unit.get("check"):
            warnings.append(f"{uid}: no check question (每单元末尾应有自测)")
        elif empty(unit["check"].get("q")):
            errors.append(f"{uid}: check.q is empty")
        if not unit.get("terms") and not any(b.get("kind") == "terms" for b in blocks):
            warnings.append(f"{uid}: no terms list for this unit")
        for qi, qa in enumerate(unit.get("qa") or [], 1):
            stats["qa"] += 1
            if empty(qa.get("question")) or empty(qa.get("answer")):
                errors.append(f"{uid} qa[{qi}]: needs question and answer")

    for i, g in enumerate(data.get("glossary") or [], 1):
        if empty(g.get("zh")) or empty(g.get("en")):
            errors.append(f"glossary[{i}]: needs zh and en")

    verdict = data.get("verdict")
    if verdict and (empty(verdict.get("supports")) or empty(verdict.get("does_not_show"))):
        errors.append("verdict needs both supports and does_not_show")

    return errors, warnings, stats


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_spec.py SPEC.json [SPEC2.json ...]", file=sys.stderr)
        return 2
    failed = 0
    for arg in sys.argv[1:]:
        path = Path(arg).resolve()
        errors, warnings, stats = validate(path)
        if errors:
            failed += 1
            print(f"SPEC INVALID: {path}")
            for e in errors:
                print(f"  - ERROR {e}")
        else:
            print(
                f"SPEC OK: {path.parent.name}/{path.name} — {stats['units']} units, {stats['blocks']} blocks, "
                f"{stats['figures']} figures, {stats['anchors']} anchored blocks, {stats['qa']} qa"
            )
        for w in warnings:
            print(f"  - warn  {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
