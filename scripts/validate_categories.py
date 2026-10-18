#!/usr/bin/env python3
"""Validate categories.json for katchup.

Shape checks (ids, deck sizes, labels, prompts, blurbs), duplicate and
near-duplicate detection within a deck, and deck-count targets. Writes
review_categories.html for the rules a script cannot judge: is this a real
deck or filler, and does every item deserve its place.

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
DATA = ROOT / "categories.json"
REVIEW = ROOT / "review_categories.html"

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

MIN_DECKS = 12
MIN_ITEMS = 12
MAX_ITEMS = 20
TARGET_ITEMS = 14
MAX_NAME = 20
MAX_PROMPT = 40
MAX_LABEL = 40
MAX_BLURB_WORDS = 12
NEAR_DUP_JACCARD = 0.5

STOP = set(
    """a an the and or but if then than that this these those to of in on for with
    at by from as is are was were be been being you your we our us i me my
    it its he she they them their""".split()
)


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate katchup categories.json")
    parser.add_argument("path", nargs="?", default=str(DATA), help="decks file (default: repo root)")
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

    deck_ids: dict[str, str] = {}
    item_counts: dict[str, int] = {}
    total_items = 0
    short_decks: list[str] = []

    for d_index, deck in enumerate(data):
        label = deck.get("id", "no id") if isinstance(deck, dict) else type(deck).__name__
        where = f"deck {d_index} ({label})"

        if not isinstance(deck, dict):
            errors.append(f"{where}: not an object")
            continue

        missing = {"id", "name", "prompt", "items"} - deck.keys()
        if missing:
            errors.append(f"{where}: missing fields {sorted(missing)}")
            continue

        did = deck["id"]
        if not isinstance(did, str) or not ID_RE.match(did):
            errors.append(f"{where}: id must be kebab-case")
        elif did in deck_ids:
            errors.append(f"{where}: duplicate deck id, first used by {deck_ids[did]}")
        else:
            deck_ids[did] = where

        name = deck["name"]
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{where}: name must be a non-empty string")
        elif len(name.strip()) > MAX_NAME:
            errors.append(f"{where}: name is {len(name)} chars, maximum {MAX_NAME} -> {name!r}")

        prompt = deck["prompt"]
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"{where}: prompt must be a non-empty string")
        elif not prompt.strip().endswith("?"):
            errors.append(f"{where}: prompt must end with '?' -> {prompt!r}")
        elif len(prompt.strip()) > MAX_PROMPT:
            errors.append(f"{where}: prompt is {len(prompt)} chars, maximum {MAX_PROMPT} -> {prompt!r}")

        items = deck["items"]
        if not isinstance(items, list):
            errors.append(f"{where}: items must be a list")
            continue

        if len(items) < MIN_ITEMS or len(items) > MAX_ITEMS:
            errors.append(
                f"{where}: {len(items)} items, want {MIN_ITEMS} to {MAX_ITEMS}"
            )
        if len(items) != TARGET_ITEMS:
            short_decks.append(f"{did} {len(items)}")
        item_counts[did if isinstance(did, str) else where] = len(items)
        total_items += len(items)

        seen_ids: dict[str, int] = {}
        seen_labels: dict[str, str] = {}
        word_sets: list[tuple[str, str, set[str]]] = []

        for i_index, item in enumerate(items):
            iwhere = f"{where} item {i_index}"
            if not isinstance(item, dict):
                errors.append(f"{iwhere}: not an object")
                continue

            missing = {"id", "label"} - item.keys()
            if missing:
                errors.append(f"{iwhere}: missing fields {sorted(missing)}")
                continue

            iid = item["id"]
            if not isinstance(iid, str) or not ID_RE.match(iid):
                errors.append(f"{iwhere}: item id must be kebab-case -> {iid!r}")
            elif iid in seen_ids:
                errors.append(f"{iwhere}: duplicate item id, first used by item {seen_ids[iid]}")
            else:
                seen_ids[iid] = i_index

            lab = item["label"]
            if not isinstance(lab, str) or not lab.strip():
                errors.append(f"{iwhere}: label must be a non-empty string")
                continue
            lab = lab.strip()
            if len(lab) > MAX_LABEL:
                errors.append(f"{iwhere}: label is {len(lab)} chars, maximum {MAX_LABEL} -> {lab!r}")

            norm = normalise(lab)
            if norm in seen_labels:
                errors.append(f"{iwhere}: duplicate label of {seen_labels[norm]!r} -> {lab!r}")
            else:
                seen_labels[norm] = lab

            blurb = item.get("blurb")
            if blurb is not None:
                if not isinstance(blurb, str) or not blurb.strip():
                    errors.append(f"{iwhere}: blurb must be a non-empty string when present")
                else:
                    words = blurb.split()
                    if len(words) > MAX_BLURB_WORDS:
                        errors.append(
                            f"{iwhere}: blurb is {len(words)} words, maximum "
                            f"{MAX_BLURB_WORDS} -> {blurb!r}"
                        )

            word_sets.append((iid if isinstance(iid, str) else f"item {i_index}", lab, significant_words(lab)))

        for i in range(len(word_sets)):
            for j in range(i + 1, len(word_sets)):
                a_id, a_label, a_words = word_sets[i]
                b_id, b_label, b_words = word_sets[j]
                if not a_words or not b_words:
                    continue
                if normalise(a_label) == normalise(b_label):
                    continue  # already reported as a duplicate label
                overlap = len(a_words & b_words) / len(a_words | b_words)
                if overlap > NEAR_DUP_JACCARD:
                    errors.append(
                        f"{where}: near-duplicate labels {a_id} / {b_id} "
                        f"({overlap:.0%}) -> {a_label!r} vs {b_label!r}"
                    )

    if len(data) < MIN_DECKS:
        noun = "deck" if len(data) == 1 else "decks"
        errors.append(f"only {len(data)} {noun}, minimum {MIN_DECKS}")

    # distribution report
    lines = [
        f"Total decks: {len(data)}  minimum {MIN_DECKS}",
        f"Total items: {total_items}",
        "",
        "Items per deck",
    ]
    for key, count in item_counts.items():
        flag = "" if count == TARGET_ITEMS else f"  (target {TARGET_ITEMS})"
        lines.append(f"  {key:24} {count:3}{flag}")

    duels = sum(max(0, count - 1) for count in item_counts.values())
    lines += ["", f"Duels if every deck is played once: {duels}"]

    print("\n".join(lines))

    target_problems: list[str] = []
    if short_decks:
        target_problems.append("decks off the 14-item target: " + ", ".join(short_decks))

    if target_problems:
        status = "FAILED" if len(data) >= MIN_DECKS else "INCOMPLETE"
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
        write_review(data, review_path, len(data), total_items)
        print(f"\nWrote {review_path}")

    return 1 if errors else 0


def write_review(data: list[dict], path: Path, deck_count: int, total_items: int) -> None:
    blocks = []
    for deck in data:
        if not isinstance(deck, dict):
            continue
        raw_items = deck.get("items")
        items: list = raw_items if isinstance(raw_items, list) else []
        rows = []
        for item in items:
            if not isinstance(item, dict):
                continue
            blurb = item.get("blurb")
            blurb_html = f'<span class="blurb">{html.escape(str(blurb))}</span>' if blurb else ""
            rows.append(
                f"<li>{html.escape(str(item.get('label', '')))} {blurb_html}</li>"
            )
        blocks.append(
            f'<section><h2>{html.escape(str(deck.get("name", "")))} '
            f'<span class="meta">{html.escape(str(deck.get("id", "")))} · '
            f'{len(items)} items · {html.escape(str(deck.get("prompt", "")))}</span></h2>'
            f"<ol>{''.join(rows)}</ol></section>"
        )

    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>katchup categories review ({deck_count} decks)</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0 auto; max-width: 52rem; padding: 2rem 1.25rem 6rem;
         font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.05rem; margin: 2rem 0 .5rem; padding-bottom: .3rem;
        border-bottom: 1px solid #8884; }}
  .meta {{ font-weight: 400; font-size: .8rem; color: #777; letter-spacing: .02em; }}
  .guide {{ border-left: 3px solid #8886; padding: .1rem 0 .1rem 1rem; color: #666; }}
  ol {{ margin: .4rem 0 0; padding-left: 1.6rem; }}
  li {{ margin: 0 0 .2rem; }}
  .blurb {{ font-size: .85rem; color: #777; }}
  @media (prefers-color-scheme: dark) {{ .guide {{ color: #aaa; }} .meta, .blurb {{ color: #999; }} }}
</style>
</head>
<body>
<h1>katchup categories review: {deck_count} decks, {total_items} items</h1>
<p class="guide">For every deck ask: would two people at a table actually argue about these
fourteen, or did some of them just fill the list? An item that nobody would defend is a
dud. A deck that reads as twelve near-synonyms has no duels in it.</p>
{"".join(blocks)}
</body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
