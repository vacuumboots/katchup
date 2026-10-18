#!/usr/bin/env bash
# Prove that the content validators fail on the rules they claim to enforce.
#
# Feeds each validator a deliberately broken fixture and asserts that every
# expected error message appears. Also asserts the real content files are
# clean of shape errors (they may still be short of the count targets while
# the content is being written).
#
# Usage: bash scripts/test_validators.sh

set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

pass=0
fail=0

expect() {
  local name="$1" haystack="$2" needle="$3"
  if printf '%s' "$haystack" | grep -qF -- "$needle"; then
    pass=$((pass + 1))
    printf '  ok    %s\n' "$name"
  else
    fail=$((fail + 1))
    printf '  FAIL  %s\n        expected: %s\n' "$name" "$needle"
  fi
}

reject() {
  local name="$1" haystack="$2" needle="$3"
  if printf '%s' "$haystack" | grep -qF -- "$needle"; then
    fail=$((fail + 1))
    printf '  FAIL  %s\n        should not contain: %s\n' "$name" "$needle"
  else
    pass=$((pass + 1))
    printf '  ok    %s\n' "$name"
  fi
}

wyr_out=$(python3 scripts/validate_wyr.py scripts/fixtures/wyr_bad.json --no-review 2>&1 || true)
cat_out=$(python3 scripts/validate_categories.py scripts/fixtures/categories_bad.json --no-review 2>&1 || true)
real_wyr=$(python3 scripts/validate_wyr.py --no-review 2>&1 || true)
real_cat=$(python3 scripts/validate_categories.py --no-review 2>&1 || true)
real_q=$(python3 scripts/validate_questions.py 2>&1 || true)

echo "would you rather: shape rules"
expect "bad id format"                 "$wyr_out" "id must match wNNNN"
expect "duplicate id"                  "$wyr_out" "duplicate id"
expect "missing field"                 "$wyr_out" "missing fields ['kind']"
expect "side too short"                "$wyr_out" "minimum 3"
expect "side too long"                 "$wyr_out" "maximum 60"
expect "empty side"                    "$wyr_out" "b must be a non-empty string"
expect "end punctuation"               "$wyr_out" "ends with punctuation '!'"
expect "identical sides"               "$wyr_out" "a and b are the same text"
expect "duplicate pair reversed"       "$wyr_out" "duplicate pair (reversed)"
expect "bad weight"                    "$wyr_out" "bad weight 'heavy'"
expect "bad topic"                     "$wyr_out" "bad topic 'gambling'"
expect "bad kind"                      "$wyr_out" "bad kind 'quiz'"
expect "frame repeated"                "$wyr_out" "repeats the frame the UI supplies"
expect "double space warning"          "$wyr_out" "double space"
expect "shape mismatch warning"        "$wyr_out" "lopsided grammatical shape"

echo "would you rather: content rules"
expect "death wording blocked"         "$wyr_out" "death wording, the one hard line"
expect "losing a person blocked"       "$wyr_out" "losing a person, the one hard line"
expect "minimum pair count"            "$wyr_out" "only 13 pairs, minimum 200"
expect "topic minimum"                 "$wyr_out" "topic gaps (minimum 8 each)"

echo "categories: shape rules"
expect "deck id not kebab-case"        "$cat_out" "id must be kebab-case"
expect "deck name too long"            "$cat_out" "maximum 20"
expect "prompt missing question mark"  "$cat_out" "prompt must end with '?'"
expect "prompt too long"               "$cat_out" "prompt is 57 chars, maximum 40"
expect "deck too small"                "$cat_out" "11 items, want 12 to 20"
expect "duplicate deck id"             "$cat_out" "duplicate deck id"
expect "duplicate item id"             "$cat_out" "duplicate item id"
expect "duplicate label"               "$cat_out" "duplicate label of 'Tuna salad'"
expect "near-duplicate labels"         "$cat_out" "near-duplicate labels grilled-cheese / grilled-cheese-sandwich (67%)"
expect "item id not kebab-case"        "$cat_out" "item id must be kebab-case"
expect "empty label"                   "$cat_out" "label must be a non-empty string"
expect "label too long"                "$cat_out" "label is 53 chars, maximum 40"
expect "blurb too long"                "$cat_out" "blurb is 13 words, maximum 12"
expect "minimum deck count"            "$cat_out" "only 3 decks, minimum 12"

echo "categories: no double reporting"
reject "exact duplicate not also near-dup" "$cat_out" "near-duplicate labels tuna-salad / tuna-salad"

echo "shipped content files"
expect "questions.json still clean"    "$real_q" "No errors."
expect "wouldrather.json validates clean"  "$real_wyr" "No errors."
expect "categories.json validates clean"  "$real_cat" "No errors."
reject "wouldrather.json is not a stub any more" "$real_wyr" "minimum 200"
reject "categories.json is not a stub any more" "$real_cat" "minimum 12"
reject "wouldrather.json has no shape errors" "$real_wyr" "bad weight"
reject "wouldrather.json has no death wording" "$real_wyr" "death wording"
reject "categories.json has no duplicate labels" "$real_cat" "duplicate label"

echo
if [ "$fail" -eq 0 ]; then
  printf 'all %d checks passed\n' "$pass"
  exit 0
fi

printf '%d of %d checks failed\n' "$fail" "$((pass + fail))"
exit 1
