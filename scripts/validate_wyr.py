#!/usr/bin/env python3
"""Validate wouldrather.json for katchup.

Shape checks (ids, sides, enums), the hard line on death and loss, duplicate
pairs in either direction, and distribution targets. Writes review_wyr.html
for the rules a script cannot judge: is one side obviously better, does the
pair land badly at a family table, are both sides the same grammatical shape.

Exit code 1 on errors, 0 otherwise (warnings and target shortfalls allowed).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "wouldrather.json"
REVIEW = ROOT / "review_wyr.html"

try:
    from validate_questions import TOPICS
except ImportError:  # run from elsewhere
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_questions import TOPICS

WEIGHTS = ["light", "medium"]
KINDS = ["dilemma", "preference", "impossible"]

ID_RE = re.compile(r"^w\d{4}$")
MIN_LEN = 3
MAX_LEN = 60
MIN_TOTAL = 200
MIN_PER_TOPIC = 8
MIN_DILEMMA_SHARE = 0.70

TARGET_LIGHT = 140
TARGET_MEDIUM = 60

END_PUNCT = ".!?;:,"

# The one hard line: death and loss of a person. Injuries are explicitly fine.
DEATH_RE = re.compile(
    r"\b(die|dies|died|dying|dead|death|deaths|kill|kills|killed|killing|"
    r"murder|murdered|murderer|funeral|funerals|grief|grieving|grieve|"
    r"mourn|mourning|casket|coffin|obituary|widow|widower|widowed|"
    r"cancer|terminal)\b",
    re.IGNORECASE,
)
LOSS_RE = re.compile(
    r"\b(lose|losing|lost|loss of)\b[^.]{0,20}\b"
    r"(mum|mom|mother|dad|father|parent|parents|brother|sister|sibling|"
    r"wife|husband|spouse|partner|son|daughter|child|kid|grandma|grandpa|"
    r"grandmother|grandfather|friend|family)\b",
    re.IGNORECASE,
)

# Editorial rules the script can only point at, not settle.
POLITICS_RE = re.compile(
    r"\b(president|prime minister|election|vote|voting|politician|government|"
    r"parliament|congress|senate|democrat|republican|liberal|conservative)\b",
    re.IGNORECASE,
)
FAITH_RE = re.compile(
    r"\b(church|god|jesus|bible|mosque|temple|synagogue|priest|pastor|pray|"
    r"religion|religious|christian|muslim|jewish|hindu)\b",
    re.IGNORECASE,
)
MONEY_RE = re.compile(
    r"\b(rich|richer|richest|poor|poorer|millionaire|billionaire|salary|"
    r"debt|mortgage|invest|investing)\b",
    re.IGNORECASE,
)

# Same grammatical shape on both sides: if one side is led by a clause opener
# and the other is not, the pair reads lopsided.
LEAD_RE = re.compile(
    r"^(never|always|only|be|have|has|get|live|eat|own|no|a|an|the)\b",
    re.IGNORECASE,
)

STOP = set(
    """a an the and or but if then than that this these those to of in on for with
    at by from as is are was were be been being you your yours we our us i me my
    it its he she they them their what which who whom when where why how
    never always only ever again""".split()
)


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def check_side(where: str, side: str, value, errors: list[str], warnings: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: {side} must be a non-empty string")
        return ""
    text = value.strip()
    if text != value:
        warnings.append(f"{where}: {side} has stray whitespace -> {value!r}")
    if len(text) < MIN_LEN:
        errors.append(f"{where}: {side} is {len(text)} chars, minimum {MIN_LEN} -> {text!r}")
    if len(text) > MAX_LEN:
        errors.append(f"{where}: {side} is {len(text)} chars, maximum {MAX_LEN} -> {text!r}")
    if text and text[-1] in END_PUNCT:
        errors.append(f"{where}: {side} ends with punctuation {text[-1]!r} -> {text!r}")
    if "  " in text:
        warnings.append(f"{where}: {side} has a double space -> {text!r}")
    if text.lower().startswith("would you rather"):
        errors.append(f"{where}: {side} repeats the frame the UI supplies -> {text!r}")
    return text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate katchup wouldrather.json")
    parser.add_argument("path", nargs="?", default=str(DATA), help="pairs file (default: repo root)")
    parser.add_argument("--review", dest="review", default=None, help="write the review page here")
    parser.add_argument("--no-review", action="store_true", help="skip the review page")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data_path = Path(args.path)
    if not data_path.exists():
        print(f"ERROR: {data_path} not found")
        return 1

    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: {data_path.name} is not valid JSON: {exc}")
        return 1

    if not isinstance(data, list):
        print(f"ERROR: {data_path.name} must be a top-level array")
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    ids: dict[str, str] = {}
    ordered_seen: dict[tuple[str, str], str] = {}
    weight: Counter = Counter()
    kind: Counter = Counter()
    topic: Counter = Counter()
    lengths: list[int] = []
    shape_hits: list[str] = []
    politics_hits: list[str] = []
    faith_hits: list[str] = []
    money_hits: list[str] = []
    death_hits: list[str] = []
    loss_hits: list[str] = []

    for index, item in enumerate(data):
        label = item.get("id", "no id") if isinstance(item, dict) else type(item).__name__
        where = f"item {index} ({label})"

        if not isinstance(item, dict):
            errors.append(f"{where}: not an object")
            continue

        missing = {"id", "a", "b", "topic", "weight", "kind"} - item.keys()
        if missing:
            errors.append(f"{where}: missing fields {sorted(missing)}")
            continue

        wid = item["id"]
        wid_valid = isinstance(wid, str) and bool(ID_RE.match(wid))
        ref = wid if wid_valid else where
        if not wid_valid:
            errors.append(f"{where}: id must match wNNNN")
        elif wid in ids:
            errors.append(f"{where}: duplicate id, first used by {ids[wid]}")
        else:
            ids[wid] = where

        a = check_side(where, "a", item["a"], errors, warnings)
        b = check_side(where, "b", item["b"], errors, warnings)

        if a and b:
            if normalise(a) == normalise(b):
                errors.append(f"{where}: a and b are the same text -> {a!r}")
            else:
                na, nb = normalise(a), normalise(b)
                if (na, nb) in ordered_seen:
                    errors.append(f"{where}: duplicate pair, first used by {ordered_seen[(na, nb)]}")
                elif (nb, na) in ordered_seen:
                    errors.append(
                        f"{where}: duplicate pair (reversed), first used by {ordered_seen[(nb, na)]}"
                    )
                else:
                    ordered_seen[(na, nb)] = ref

            if bool(LEAD_RE.match(a)) != bool(LEAD_RE.match(b)):
                shape_hits.append(f"{wid}: {a!r} / {b!r}")

            both = " ".join((a, b))
            for term in DEATH_RE.findall(both):
                death_hits.append(f"{wid}: {term}")
            for match in LOSS_RE.finditer(both):
                loss_hits.append(f"{wid}: {match.group(0)!r}")
            for term in POLITICS_RE.findall(both):
                politics_hits.append(f"{wid}: {term}")
            for term in FAITH_RE.findall(both):
                faith_hits.append(f"{wid}: {term}")
            for term in MONEY_RE.findall(both):
                money_hits.append(f"{wid}: {term}")

            lengths.append(max(len(a), len(b)))

        if item["weight"] not in WEIGHTS:
            errors.append(f"{where}: bad weight {item['weight']!r}, want one of {WEIGHTS}")
        else:
            weight[item["weight"]] += 1

        if item["kind"] not in KINDS:
            errors.append(f"{where}: bad kind {item['kind']!r}, want one of {KINDS}")
        else:
            kind[item["kind"]] += 1

        if item["topic"] not in TOPICS:
            errors.append(f"{where}: bad topic {item['topic']!r}, want one of {TOPICS}")
        else:
            topic[item["topic"]] += 1

    total = len(data)

    if total < MIN_TOTAL:
        errors.append(f"only {total} pairs, minimum {MIN_TOTAL}")

    gaps = [f"{key} {topic[key]}/{MIN_PER_TOPIC}" for key in TOPICS if topic[key] < MIN_PER_TOPIC]
    if gaps:
        errors.append(f"topic gaps (minimum {MIN_PER_TOPIC} each): " + ", ".join(gaps))

    if death_hits:
        errors.append("death wording, the one hard line: " + "; ".join(death_hits))
    if loss_hits:
        errors.append("losing a person, the one hard line: " + "; ".join(loss_hits))

    if politics_hits:
        warnings.append("politics, keep it out: " + "; ".join(politics_hits))
    if faith_hits:
        warnings.append("religion, keep it out: " + "; ".join(faith_hits))
    if money_hits:
        warnings.append("money status, check one side is not obviously better: " + "; ".join(money_hits))
    if shape_hits:
        warnings.append("lopsided grammatical shape: " + "; ".join(shape_hits))

    # distribution report
    lines = [f"Total pairs: {total}/{MIN_TOTAL}", "", "Weight"]
    for key, target in (("light", TARGET_LIGHT), ("medium", TARGET_MEDIUM)):
        lines.append(f"  {key:7} {weight[key]:4}  target {target}")

    lines += ["", f"Topic (minimum {MIN_PER_TOPIC} each)"]
    for key in TOPICS:
        lines.append(f"  {key:9} {topic[key]:4}")

    lines += ["", "Kind"]
    for key in KINDS:
        share = kind[key] / total if total else 0
        lines.append(f"  {key:12} {kind[key]:4}  {share:6.1%}")
    dilemma_share = kind["dilemma"] / total if total else 0
    lines.append(f"  dilemma share required: {MIN_DILEMMA_SHARE:.0%}, actual {dilemma_share:.1%}")

    if lengths:
        lines += ["", "Longest side", f"  min {min(lengths)}, max {max(lengths)}, limit {MAX_LEN}"]

    print("\n".join(lines))

    target_problems: list[str] = []
    if weight["light"] != TARGET_LIGHT:
        target_problems.append(f"light is {weight['light']}, want {TARGET_LIGHT}")
    if weight["medium"] != TARGET_MEDIUM:
        target_problems.append(f"medium is {weight['medium']}, want {TARGET_MEDIUM}")
    if total and dilemma_share < MIN_DILEMMA_SHARE:
        target_problems.append(
            f"dilemma is {kind['dilemma']}/{total} = {dilemma_share:.1%}, want at least "
            f"{MIN_DILEMMA_SHARE:.0%}"
        )
    if total != MIN_TOTAL:
        target_problems.append(f"deck has {total} pairs, want {MIN_TOTAL}")

    if target_problems:
        status = "INCOMPLETE" if total != MIN_TOTAL else "FAILED"
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

    review_path = Path(args.review) if args.review else REVIEW
    if not args.no_review and (args.review or data_path.resolve() == DATA.resolve()):
        write_review(data, review_path, total)
        print(f"\nWrote {review_path}")

    return 1 if errors else 0


def write_review(data: list[dict], path: Path, total: int) -> None:
    cards = []
    for item in data:
        if not isinstance(item, dict):
            continue
        a = html.escape(str(item.get("a", "")))
        b = html.escape(str(item.get("b", "")))
        tags = " · ".join(str(item.get(field, "")) for field in ("topic", "weight", "kind"))
        cards.append(
            f'<li><p class="pair">Would you rather <b>{a}</b> or <b>{b}</b>?</p>'
            f'<p class="tags">{html.escape(str(item.get("id", "")))} · {html.escape(tags)}</p></li>'
        )

    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>katchup would-you-rather review ({total} pairs)</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0 auto; max-width: 46rem; padding: 2rem 1.25rem 6rem;
         font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  h1 {{ font-size: 1.4rem; }}
  .guide {{ border-left: 3px solid #8886; padding: .1rem 0 .1rem 1rem; color: #666; }}
  ol {{ padding-left: 2.5rem; }}
  li {{ margin: 0 0 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #8884; }}
  li::marker {{ color: #888; font-size: .85rem; }}
  .pair {{ font-size: 1.05rem; margin: 0 0 .3rem; }}
  .tags {{ font-size: .8rem; color: #777; margin: 0; letter-spacing: .02em; }}
  @media (prefers-color-scheme: dark) {{ .guide {{ color: #aaa; }} .tags {{ color: #999; }} }}
</style>
</head>
<body>
<h1>katchup would-you-rather review: {total} pairs</h1>
<p class="guide">Read the whole list once, out loud if you can. For every pair ask: is one
side obviously better, would the pair land badly at a family table, and do both sides have
the same grammatical shape. Injuries and mishaps are wanted. Death and loss of a person are
out. The validator cannot judge any of this, which makes this page the real gate.</p>
<ol>
{"".join(cards)}
</ol>
</body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
