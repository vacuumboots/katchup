#!/usr/bin/env bash
# Run every katchup content validator. Exits non-zero if any of them fails.
#
# Usage: bash scripts/validate_all.sh
#
# Each validator prints its own distribution report and errors. This wrapper
# only adds a summary line at the end so a failing file is obvious at a glance.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

VALIDATORS=(
  validate_questions.py
  validate_wyr.py
  validate_categories.py
)

failed=()

for script in "${VALIDATORS[@]}"; do
  printf '\n=== %s ===\n' "$script"
  if ! python3 "scripts/$script"; then
    failed+=("$script")
  fi
done

printf '\n=== summary ===\n'
if [ ${#failed[@]} -eq 0 ]; then
  printf 'all %d validators passed\n' "${#VALIDATORS[@]}"
  exit 0
fi

printf '%d of %d validators failed: %s\n' \
  "${#failed[@]}" "${#VALIDATORS[@]}" "${failed[*]}"
exit 1
