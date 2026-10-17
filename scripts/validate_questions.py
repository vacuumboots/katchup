#!/usr/bin/env python3
"""Validate questions.json for katchup.

Checks shape (ids, enums, followups, punctuation), flags yes/no openers and
near-duplicates, prints the distributions against the spec targets, and writes
review.html: one page with every question, for a single human read-through.

Exit code 1 on hard errors, 0 otherwise (warnings allowed).
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "questions.json"
REVIEW = ROOT / "review.html"

ERAS = ["childhood", "teens", "young-adult", "career", "family", "now"]
TOPICS = [
    "music", "food", "cars", "work", "school", "places", "home",
    "firsts", "people", "money", "hobbies", "media", "advice",
]
WEIGHTS = ["light", "medium", "heavy"]
KINDS = ["memory", "opinion", "hypothetical"]

TARGET_TOTAL = 300
TARGET_LIGHT = 195
TARGET_MEDIUM = 90
TARGET_HEAVY = 15
TARGET_MEMORY_MIN = 180
TARGET_PER_ERA_MIN = 10
TARGET_PER_TOPIC_MIN = 10
MAX_LEN = 120

ID_RE = re.compile(r"^q\d{4}$")
YES_NO_RE = re.compile(
    r"^(do|did|does|have|has|had|are|is|was|were|can|could|would|will|should|"
    r"shall|may|might|am)\b",
    re.IGNORECASE,
)

STOP = set(
    """a an the and or but if then than that this these those to of in on for with
    at by from as is are was were be been being you your yours we our us i me my
    it its he she they them their what which who whom when where why how""".split()
)


def significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def main() -> int:
    if not QUESTIONS.exists():
        print(f"ERROR: {QUESTIONS} not found")
        return 1

    try:
        data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: questions.json is not valid JSON: {exc}")
        return 1

    if not isinstance(data, list):
        print("ERROR: questions.json must be a top-level array")
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    ids: set[str] = set()
    texts: dict[str, str] = {}
    weight: dict[str, int] = {w: 0 for w in WEIGHTS}
    kind: dict[str, int] = {k: 0 for k in KINDS}
    era: dict[str, int] = {e: 0 for e in ERAS}
    topic: dict[str, int] = {t: 0 for t in TOPICS}
    word_sets: list[tuple[str, str, set[str]]] = []

    for index, item in enumerate(data):
        where = f"item {index} ({item.get('id', 'no id') if isinstance(item, dict) else type(item).__name__})"

        if not isinstance(item, dict):
            errors.append(f"{where}: not an object")
            continue

        missing = {"id", "text", "era", "topic", "weight", "kind", "followups"} - item.keys()
        if missing:
            errors.append(f"{where}: missing fields {sorted(missing)}")
            continue

        qid = item["id"]
        text = item["text"]

        if not isinstance(qid, str) or not ID_RE.match(qid):
            errors.append(f"{where}: id must match qNNNN")
        elif qid in ids:
            errors.append(f"{where}: duplicate id")
        else:
            ids.add(qid)

        if not isinstance(text, str) or not text.strip():
            errors.append(f"{where}: text must be a non-empty string")
            continue
        text = text.strip()

        if not text.endswith("?"):
            errors.append(f"{where}: text must end with '?' -> {text!r}")
        if text.endswith("??") or "?" in text[:-1]:
            warnings.append(f"{where}: more than one question mark -> {text!r}")
        if len(text) > MAX_LEN:
            warnings.append(f"{where}: {len(text)} chars (target under {MAX_LEN}) -> {text!r}")
        if YES_NO_RE.match(text):
            errors.append(f"{where}: yes/no opener -> {text!r}")

        norm = normalise(text)
        if norm in texts:
            errors.append(f"{where}: duplicate text of {texts[norm]} -> {text!r}")
        else:
            texts[norm] = qid

        if item["era"] not in ERAS:
            errors.append(f"{where}: bad era {item['era']!r}")
        else:
            era[item["era"]] += 1

        if item["topic"] not in TOPICS:
            errors.append(f"{where}: bad topic {item['topic']!r}")
        else:
            topic[item["topic"]] += 1

        if item["weight"] not in WEIGHTS:
            errors.append(f"{where}: bad weight {item['weight']!r}")
        else:
            weight[item["weight"]] += 1

        if item["kind"] not in KINDS:
            errors.append(f"{where}: bad kind {item['kind']!r}")
        else:
            kind[item["kind"]] += 1

        followups = item["followups"]
        if not isinstance(followups, list) or not 1 <= len(followups) <= 3:
            errors.append(f"{where}: followups must be a list of 1 to 3 entries")
        else:
            for followup in followups:
                if not isinstance(followup, str) or not followup.strip():
                    errors.append(f"{where}: empty followup")
                elif not followup.strip().endswith("?"):
                    errors.append(f"{where}: followup must end with '?' -> {followup!r}")

        word_sets.append((qid, text, significant_words(text)))

    # near-duplicate pairs
    for i in range(len(word_sets)):
        for j in range(i + 1, len(word_sets)):
            a_id, a_text, a_words = word_sets[i]
            b_id, b_text, b_words = word_sets[j]
            if not a_words or not b_words:
                continue
            overlap = len(a_words & b_words) / len(a_words | b_words)
            if overlap > 0.5:
                warnings.append(
                    f"near-duplicate {a_id} / {b_id} ({overlap:.0%}): "
                    f"{a_text!r} vs {b_text!r}"
                )

    # distribution report
    total = len(data)
    lines: list[str] = []
    lines.append(f"Total questions: {total}/{TARGET_TOTAL}")

    lines.append("")
    lines.append("Weight")
    for key, target in (("light", TARGET_LIGHT), ("medium", TARGET_MEDIUM), ("heavy", TARGET_HEAVY)):
        lines.append(f"  {key:7} {weight[key]:4}  target {target}")

    lines.append("")
    lines.append("Kind")
    for key in KINDS:
        note = f"  target at least {TARGET_MEMORY_MIN}" if key == "memory" else ""
        lines.append(f"  {key:12} {kind[key]:4}{note}")

    lines.append("")
    lines.append("Era")
    for key in ERAS:
        lines.append(f"  {key:12} {era[key]:4}  target at least {TARGET_PER_ERA_MIN}")

    lines.append("")
    lines.append("Topic")
    for key in TOPICS:
        lines.append(f"  {key:9} {topic[key]:4}  target at least {TARGET_PER_TOPIC_MIN}")

    # target enforcement only once the deck is complete
    target_problems: list[str] = []
    if weight["light"] != TARGET_LIGHT:
        target_problems.append(f"light is {weight['light']}, want {TARGET_LIGHT}")
    if weight["medium"] != TARGET_MEDIUM:
        target_problems.append(f"medium is {weight['medium']}, want {TARGET_MEDIUM}")
    if weight["heavy"] != TARGET_HEAVY:
        target_problems.append(f"heavy is {weight['heavy']}, want {TARGET_HEAVY}")
    if kind["memory"] < TARGET_MEMORY_MIN:
        target_problems.append(f"memory is {kind['memory']}, want at least {TARGET_MEMORY_MIN}")
    for key, value in era.items():
        if value < TARGET_PER_ERA_MIN:
            target_problems.append(f"era {key} has {value}, want at least {TARGET_PER_ERA_MIN}")
    for key, value in topic.items():
        if value < TARGET_PER_TOPIC_MIN:
            target_problems.append(f"topic {key} has {value}, want at least {TARGET_PER_TOPIC_MIN}")
    if total != TARGET_TOTAL:
        target_problems.append(f"deck has {total} questions, want {TARGET_TOTAL}")

    print("\n".join(lines))

    if target_problems:
        status = "INCOMPLETE" if total != TARGET_TOTAL else "FAILED"
        print(f"\nDistribution targets {status}:")
        for problem in target_problems:
            print(f"  - {problem}")
    else:
        print("\nDistribution targets: all met")

    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\nNo errors.")

    write_review(data)
    print(f"\nWrote {REVIEW.relative_to(ROOT)}")

    return 1 if errors else 0


def write_review(data: list[dict]) -> None:
    rows = []
    for number, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        tags = " · ".join(
            str(item.get(field, "")) for field in ("era", "topic", "weight", "kind")
        )
        followups = "".join(
            f"<li>{html.escape(str(followup))}</li>" for followup in item.get("followups", [])
        )
        rows.append(
            f'<li><p class="q">{html.escape(str(item.get("text", "")))}</p>'
            f'<p class="tags">{html.escape(tags)}</p>'
            f"<ul class=\"fu\">{followups}</ul></li>"
        )

    REVIEW.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>katchup review ({len(data)} questions)</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0 auto; max-width: 46rem; padding: 2rem 1.25rem 6rem;
         font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  h1 {{ font-size: 1.4rem; }}
  ol {{ padding-left: 2.5rem; }}
  li {{ margin: 0 0 1.75rem; padding-bottom: 1.25rem; border-bottom: 1px solid #8884; }}
  li::marker {{ color: #888; font-size: .85rem; }}
  .q {{ font-size: 1.15rem; font-weight: 600; margin: 0 0 .3rem; }}
  .tags {{ font-size: .8rem; color: #777; margin: 0 0 .4rem; letter-spacing: .02em; }}
  .fu {{ margin: 0; padding-left: 1.1rem; font-size: .9rem; color: #555; }}
  @media (prefers-color-scheme: dark) {{ .fu {{ color: #aaa; }} .tags {{ color: #999; }} }}
</style>
</head>
<body>
<h1>katchup review: {len(data)} questions</h1>
<p>Read the whole list once. Fix anything that feels like filler, sound like a survey,
or opens the same door as another question.</p>
<ol>
{"".join(rows)}
</ol>
</body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
