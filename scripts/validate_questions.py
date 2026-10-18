#!/usr/bin/env python3
"""Validate questions.json for katchup.

Shape checks (ids, enums, follow-ups, punctuation), content rules (yes/no
openers, opener variety, the word "first", dialect), duplicate and
near-duplicate detection, distribution targets, and review.html output.

Exit code 1 on errors, 0 otherwise (warnings allowed).
"""

from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "questions.json"
REVIEW = ROOT / "review.html"

ERAS = ["childhood", "teens", "young-adult", "career", "midlife", "now"]
TOPICS = [
    "music", "food", "cars", "work", "school", "places", "home",
    "firsts", "people", "money", "hobbies", "media", "advice",
]
WEIGHTS = ["light", "medium", "heavy"]
KINDS = ["memory", "opinion", "hypothetical"]
HOOKS = ["extreme", "measure", "artifact", "relational", "scene", "debate", "plain"]

TARGET_TOTAL = 329
TARGET_LIGHT = 220
TARGET_MEDIUM = 94
TARGET_HEAVY = 15
MIN_PER_ERA = 15
MIN_PER_TOPIC = 10
MAX_LEN = 120

OPENER_CAP_SHARE = 0.15
MIN_STRONG_HOOK_SHARE = 0.40   # extreme + measure + artifact + relational + scene
MIN_MEASURED_SHARE = 0.10      # extreme + measure
MAX_DEBATE_SHARE = 0.05
MAX_FAVOURITE_SHARE = 0.05
STRONG_HOOKS = ("extreme", "measure", "artifact", "relational", "scene")
BANNED_PHRASES = ["biggest impact", "most influential"]       # no two-word opener above this share of the deck
MAX_WHAT_WAS_THE_FIRST = 10
MAX_FIRST_WORD = 30
MAX_WHO_FOLLOWUP_SHARE = 0.25
FOLLOWUPS_PER_QUESTION = 2
HEAVY_SHARE = (0.05, 0.10)

# Canadian audience: these read as British or Australian, not Canadian
DIALECT_BLOCK = [
    "fortnight", "payslip", "petrol", "lorry", "telly", "mum", "whilst",
    "amongst", "learnt", "spelt", "programme", "cosy", "nappy", "pram",
]

ID_RE = re.compile(r"^q\d{4}$")
YES_NO_RE = re.compile(
    r"^(do|did|does|have|has|had|are|is|was|were|can|could|would|will|should|"
    r"shall|may|might|am)\b",
    re.IGNORECASE,
)
FIRST_RE = re.compile(r"\bfirst\b", re.IGNORECASE)
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


def opener(text: str) -> str:
    return " ".join(text.split()[:2])


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
    weight: Counter = Counter()
    kind: Counter = Counter()
    era: Counter = Counter()
    topic: Counter = Counter()
    openers: Counter = Counter()
    hooks: Counter = Counter()
    hook_errors: list[str] = []
    was_the_first: list[str] = []
    dialect_hits: list[str] = []
    word_sets: list[tuple[str, str, set[str]]] = []
    followups: list[str] = []

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

        openers[opener(text)] += 1
        if text.lower().startswith("what was the first"):
            was_the_first.append(qid)

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

        if item.get("hook") not in HOOKS:
            errors.append(f"{where}: bad hook {item.get('hook')!r}")
        else:
            hooks[item["hook"]] += 1

        for phrase in BANNED_PHRASES:
            if phrase in text.lower():
                hook_errors.append(f"{qid}: banned phrasing {phrase!r}")

        raw_followups = item["followups"]
        if not isinstance(raw_followups, list) or len(raw_followups) != FOLLOWUPS_PER_QUESTION:
            errors.append(f"{where}: followups must be a list of exactly {FOLLOWUPS_PER_QUESTION}")
            raw_followups = raw_followups if isinstance(raw_followups, list) else []

        for followup in raw_followups:
            if not isinstance(followup, str) or not followup.strip():
                errors.append(f"{where}: empty followup")
                continue
            followup = followup.strip()
            if not followup.endswith("?"):
                errors.append(f"{where}: followup must end with '?' -> {followup!r}")
            if YES_NO_RE.match(followup):
                errors.append(f"{where}: yes/no followup -> {followup!r}")
            followups.append(followup)

        if len(raw_followups) == FOLLOWUPS_PER_QUESTION and all(isinstance(f, str) for f in raw_followups):
            firsts = [f.strip().split()[0].lower() for f in raw_followups if f.strip()]
            if len(firsts) == 2 and firsts[0] == firsts[1]:
                errors.append(f"{where}: both followups start with {firsts[0]!r}")

        for term in DIALECT_BLOCK:
            if re.search(r"\b" + term, text + " " + " ".join(raw_followups), re.I):
                dialect_hits.append(f"{qid}: {term}")

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

    total = len(data)

    # opener variety
    for key, count in openers.items():
        share = count / total if total else 0
        if share > OPENER_CAP_SHARE:
            errors.append(
                f"opener {key!r} used {count} times ({share:.1%}), cap is {OPENER_CAP_SHARE:.0%}"
            )
    if len(was_the_first) > MAX_WHAT_WAS_THE_FIRST:
        errors.append(
            f'"What was the first" starts {len(was_the_first)} questions, '
            f"cap is {MAX_WHAT_WAS_THE_FIRST}: {was_the_first}"
        )

    first_count = sum(
        1 for q in data
        if isinstance(q, dict) and isinstance(q.get("text"), str) and FIRST_RE.search(q["text"])
    )
    if first_count > MAX_FIRST_WORD:
        errors.append(f"the word 'first' appears in {first_count} questions, cap is {MAX_FIRST_WORD}")

    who_followups = sum(1 for f in followups if f.lower().startswith("who"))
    if followups and who_followups / len(followups) > MAX_WHO_FOLLOWUP_SHARE:
        errors.append(
            f"'Who' followups are {who_followups}/{len(followups)} = "
            f"{who_followups / len(followups):.1%}, cap is {MAX_WHO_FOLLOWUP_SHARE:.0%}"
        )

    if dialect_hits:
        errors.append("non-Canadian wording: " + ", ".join(dialect_hits))

    if hook_errors:
        errors.append("hook phrasing: " + "; ".join(hook_errors))

    strong_hooks = sum(hooks[k] for k in STRONG_HOOKS)
    measured = hooks["extreme"] + hooks["measure"]
    favourite = sum(
        1 for q in data
        if isinstance(q, dict) and isinstance(q.get("text"), str)
        and re.search(r"favou?rite", q["text"], re.I)
    )
    if total:
        if strong_hooks / total < MIN_STRONG_HOOK_SHARE:
            errors.append(
                f"strong hooks are {strong_hooks}/{total} = {strong_hooks / total:.1%}, "
                f"want at least {MIN_STRONG_HOOK_SHARE:.0%}"
            )
        if measured / total < MIN_MEASURED_SHARE:
            errors.append(
                f"measurable extremes are {measured}/{total} = {measured / total:.1%}, "
                f"want at least {MIN_MEASURED_SHARE:.0%}"
            )
        if hooks["debate"] / total > MAX_DEBATE_SHARE:
            errors.append(
                f"debate is {hooks['debate']}/{total} = {hooks['debate'] / total:.1%}, "
                f"cap is {MAX_DEBATE_SHARE:.0%}"
            )
        if favourite / total > MAX_FAVOURITE_SHARE:
            errors.append(
                f"'favourite' questions are {favourite}/{total} = {favourite / total:.1%}, "
                f"cap is {MAX_FAVOURITE_SHARE:.0%}"
            )

    # distribution report
    lines = [f"Total questions: {total}/{TARGET_TOTAL}", "", "Weight"]
    for key, target in (("light", TARGET_LIGHT), ("medium", TARGET_MEDIUM), ("heavy", TARGET_HEAVY)):
        lines.append(f"  {key:7} {weight[key]:4}  target {target}")

    lines += ["", "Kind"]
    for key in KINDS:
        lines.append(f"  {key:12} {kind[key]:4}")

    lines += ["", "Era"]
    for key in ERAS:
        lines.append(f"  {key:12} {era[key]:4}  minimum {MIN_PER_ERA}")

    lines += ["", "Topic"]
    for key in TOPICS:
        lines.append(f"  {key:9} {topic[key]:4}  minimum {MIN_PER_TOPIC}")

    lines += ["", "Openers (two words)"]
    for key, count in openers.most_common(10):
        lines.append(f"  {key:16} {count:4}  {count / total:5.1%}")
    lines.append(f"  distinct openers: {len(openers)}")
    lines.append(f"  'What was the first' starts: {len(was_the_first)}  cap {MAX_WHAT_WAS_THE_FIRST}")
    lines.append(f"  questions containing 'first': {first_count}  cap {MAX_FIRST_WORD}")

    lines += ["", "Follow-ups"]
    lines.append(
        f"  total {len(followups)}, 'Who' {who_followups} "
        f"({who_followups / max(1, len(followups)):.1%})"
    )

    lines += ["", "Hooks"]
    for key in HOOKS:
        share = hooks[key] / total if total else 0
        lines.append(f"  {key:12} {hooks[key]:4}  {share:6.1%}")
    lines.append(
        f"  strong (extreme+measure+artifact+relational+scene): "
        f"{sum(hooks[k] for k in STRONG_HOOKS)} "
        f"({sum(hooks[k] for k in STRONG_HOOKS) / total:.1%})"
    )
    lines.append(
        f"  measurable extremes (extreme+measure): {hooks['extreme'] + hooks['measure']} "
        f"({(hooks['extreme'] + hooks['measure']) / total:.1%})"
    )
    lines.append(f"  'favourite' questions: {favourite if total else 0}")

    # warmth, reported and never enforced: this is a deck for a family to play together,
    # so a pass that only sharpens the questions makes it colder every time
    family_re = re.compile(
        r"\b(mothers?|fathers?|mums?|dads?|parents?|mother-in-law|father-in-law|"
        r"grandmother|grandfather|grandma|grandpa|nana|aunt|uncle|cousin|sister|brother|"
        r"family|relative)\b",
        re.IGNORECASE,
    )
    named = sum(1 for item in data if family_re.search(item.get("text", "")))
    why = sum(
        1
        for item in data
        for f in item.get("followups", [])
        if f.strip().lower().startswith("why")
    )
    lines.append("")
    lines.append("Warmth (reported, not enforced)")
    lines.append(
        f"  cards naming a family member: {named} ({named / total:.0%})"
        if total
        else "  cards naming a family member: 0"
    )
    lines.append(f"  follow-ups starting 'Why': {why}")

    print("\n".join(lines))

    target_problems: list[str] = []
    if weight["light"] != TARGET_LIGHT:
        target_problems.append(f"light is {weight['light']}, want {TARGET_LIGHT}")
    if weight["medium"] != TARGET_MEDIUM:
        target_problems.append(f"medium is {weight['medium']}, want {TARGET_MEDIUM}")
    if weight["heavy"] != TARGET_HEAVY:
        target_problems.append(f"heavy is {weight['heavy']}, want {TARGET_HEAVY}")
    if total:
        heavy_share = weight["heavy"] / total
        # the tier is held at 15 questions, which is about 5% and drifts under it as the deck grows
        if weight["heavy"] < TARGET_HEAVY or heavy_share > HEAVY_SHARE[1]:
            target_problems.append(
                f"heavy is {weight['heavy']} ({heavy_share:.1%} of the deck), want at least "
                f"{TARGET_HEAVY} questions and no more than {HEAVY_SHARE[1]:.0%}"
            )
    for key in ERAS:
        if era[key] < MIN_PER_ERA:
            target_problems.append(f"era {key} has {era[key]}, want at least {MIN_PER_ERA}")
    for key in TOPICS:
        if topic[key] < MIN_PER_TOPIC:
            target_problems.append(f"topic {key} has {topic[key]}, want at least {MIN_PER_TOPIC}")
    if total != TARGET_TOTAL:
        target_problems.append(f"deck has {total} questions, want {TARGET_TOTAL}")

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
    for item in data:
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
            f'<p class="tags">{html.escape(str(item.get("id", "")))} · {html.escape(tags)}</p>'
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
