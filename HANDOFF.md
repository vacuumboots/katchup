# katchup — handoff

Written 2026-10-17 at the end of a long session. Read this first, then the plan it
points at. It should take five minutes to be productive again.

## What this is

A phone-first conversation game. One card at a time, no accounts, no backend, no
analytics, no AI at runtime. Static files, served over HTTPS, installable as a home
screen shortcut (no service worker, no offline mode, by decision).

- Repo: `~/Git/katchup`, branch `main`
- Live: https://vacuumboots.github.io/katchup/ (GitHub Pages, deployed from `main` root)
- Remote: https://github.com/vacuumboots/katchup (public, account `vacuumboots`)
- Spec: `mvpspec.md` (the original MVP brief, amended as the product changed)
- README: `README.md` (how to run, deploy, and add content)

## Status right now

- **309 questions**, all validated: 203 light / 91 medium / 15 heavy.
- Eras: childhood 88, now 64, teens 53, young-adult 48, career 41, midlife 15.
- Hooks: relational 58, scene 26, artifact 25, extreme 24, measure 9, debate 1,
  plain 166. Strong-hook mix 46%, measurable extremes 10.7%.
- `python3 scripts/validate_questions.py` exits 0, no errors, no warnings.
- Six commits on `main`: spec, MVP, `.nojekyll`, README link, deck revision, hook
  field + anchors.
- Local dev server was running on <http://127.0.0.1:8099> at handoff. If it is dead:
  `python3 -m http.server 8099` from the repo root.

The app is one mode today: open-ended questions, with Asked it / Skip / Never, Back as
one-level undo, filters, stats, export/import.

## The work in flight: three game modes

The next feature turns one game into three, chosen on a home screen:

1. **Open ended** — what already ships.
2. **Would you rather random** — dilemma pairs, two options, pick one, next.
3. **Would you rather Categories** — a category deck where the winner stays on and
   faces the next item until one champion is left.

**The plan is on disk at `.hermes/plans/2026-10-17_174723-katchup-three-modes.md`.**
It is deliberately gitignored (`.hermes/` in `.gitignore`), so it does not travel with
the repo, only with this machine. Read it before touching code: it has screen specs,
data schemas, route names, state shapes, validator rules, the phase-by-phase build
order, and the verification steps.

Nothing of the three-mode work is built. No app code has been changed for it.

### Decisions already locked (do not re-litigate)

- Mode labels: `Open ended`, `Would you rather random`, `Would you rather Categories`.
- Routes: `#`, `#open`, `#random`, `#categories`, `#categories/<id>`,
  `#categories/<id>/done`.
- **No sessions.** Every entry starts fresh. Nothing resumes or expires. Repeats across
  visits are fine because one tap skips. Persisted state is only the open-ended deck's
  asked/never/history, plus two independent filter sets.
- **No scoring.** No points, streaks, or pick history.
- Filters exist in both question modes, with **independent settings** (`Filters` in each
  header); the random mode stores only `katchup_random_v1` = its filters.
- Content is generic for **Canada and the US**. No local decks, no single-country chains.
- **Tone line for would-you-rather: death and loss are out.** Nothing about dying,
  killing, funerals, grief, or losing a person. Injuries and mishaps are allowed and
  wanted, 5-10 of the 200 pairs, nothing past a black eye or a broken arm.
- Category count: **12 decks**, 14 items each. Music artists stays one mixed-era deck
  for now; splitting it into 60s-80s and 90s-now is a later one-file change that would
  make it 13.

### Next step

Phase 1 of the plan: write `scripts/validate_wyr.py`,
`scripts/validate_categories.py`, and `scripts/validate_all.sh`, plus a 6-pair and a
1-deck stub to prove the validators fail on the right rules. Do not touch `app.js` in
Phase 1.

After that, Phase 2 is the only risky step: split `app.js` into `app-core.js` +
`app-open.js`, add the router and home screen, and prove the existing mode still passes
the harness below before adding any new screen.

## Commands

```sh
cd ~/Git/katchup

# local server (leave running in a background terminal)
python3 -m http.server 8099

# content gate, run before every commit that touches content
python3 scripts/validate_questions.py     # also writes review.html
# (later) bash scripts/validate_all.sh

# ship: Pages rebuilds on push to main
git add -A && git commit -m "..." && git push origin main

# confirm the deploy actually rebuilt, not just that the push worked
gh api repos/vacuumboots/katchup/pages --jq .status    # wait for "built"
curl -s https://vacuumboots.github.io/katchup/questions.json | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
```

`gh` is authenticated as `vacuumboots` with `repo` scope. Pages is served from `main`,
root path, with `.nojekyll` in place. The first build after adding Pages errored once
and the rebuild came back clean, so a single `errored` status is not necessarily fatal.

## Verification harness

There is no test suite in the repo. The checks live in a scratch directory that shares
the same machine, using puppeteer-core pointed at the Playwright chromium that is
already downloaded:

- Scripts: `~/.hermes/cache/scratch/katchup-test/` (`test.js` is the main one;
  `verify.js` does worst-case layout, `contrast.js` does colour ratios, `shots.js` and
  `live.js` do screenshots and the deployed-site check).
- Browser: `~/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell`
- Run: `cd ~/.hermes/cache/scratch/katchup-test && node test.js`
- Note: the browser tool refuses localhost URLs, which is why this is puppeteer over the
  CLI instead.

What `test.js` currently proves: layout at 375x667 (question font 28px, no scroll, the
three actions inside the bottom quarter), ask three / undo restores the card and drops
it from `asked`, skip and never and their undo, follow-ups toggle, filters narrow to
heavy with an accurate count, reload keeps `asked` and the current card, empty state
when everything is asked, export/import round trip, zero network requests after load,
zero console errors, plus dark/light screenshots.

Extend that harness (or copy it into `scripts/` as a committed smoke test) when the new
modes land. It is the only thing that has caught real bugs here.

## Code map

```
index.html            one screen: header, card, 3 actions, filters sheet, stats sheet
app.js                564 lines, everything: state, selection, undo, filters, export
styles.css            gruvbox light/dark, 76px actions, [hidden] override
questions.json        309 questions, the deck
scripts/validate_questions.py   validator + review.html emitter (449 lines)
manifest.webmanifest  home-screen shortcut only
icons/                192 and 512 placeholder PNGs
mvpspec.md            the brief, amended
review.html           generated by the validator, gitignored
```

Key app.js anchors: `defaultState()` 63, `migrate()` 76, `pickNext()` 152,
`showCard()` 173, `advance()` 230, `act()` 246, `undo()` 267, `openSheet()` 300,
`renderFilters()` 318, `wire()` 449, `boot()` at the bottom.

Data model for a question: `id`, `text`, `era`, `topic`, `weight`, `kind`, `hook`,
`followups` (exactly two, ending in `?`).

## Content rules (they are enforced, do not "improve" them casually)

Questions:
- Under ~100 chars, one sentence, ends in `?`, never yes/no, never starting Do / Can /
  Is / Are / Would / Have.
- No two-word opener above 15% of the deck (currently "What was" 12.0%, "What is" 11.0%).
- At most 10 questions starting "What was the first"; at most 30 containing "first".
- Exactly two follow-ups; no yes/no follow-ups; the two must not start with the same
  word; "Who" follow-ups capped at 25%.
- Era minimum 15 each, topic minimum 10 each; heavy tier held at 15 questions.
- Hook mix: strong set (extreme+measure+artifact+relational+scene) at least 40%,
  extreme+measure at least 10%, debate at most 5%, "favourite" at most 5%.
- Canadian English: colour, favourite, neighbour, theatre, travelled, paycheque. Banned:
  fortnight, payslip, petrol, lorry, telly, mum, whilst, amongst, learnt, spelt,
  programme, cosy, nappy, pram. Canadian and US audiences both, so no local references.
- No "biggest impact" or "most influential" phrasing.

Would-you-rather (not written yet): `a`/`b` 3-60 chars, no end punctuation, same
grammatical shape both sides, light or medium only, death/loss blocklist, no
obviously-better pair, no duplicate pair in either direction.

## Known issues / deliberately deferred

1. **Era chips in the app are stale.** `app.js` still hardcodes
   `["childhood","teens","young-adult","career","family","now"]`, so the Filters sheet
   shows a `family` chip that matches nothing and has no `midlife` chip; the 15 midlife
   questions are only reachable under `All`. The fix is one line in `VALUES.era`. It was
   left alone because the instruction at the time was "do not change the app code". Fix
   it in Phase 2 when `app.js` is being split anyway.
2. `review.html` and the two planned review pages are gitignored; regenerate rather than
   commit them.
3. Heavy is 15 questions = 4.9% of 309. The validator floors at 15 questions and caps at
   10% rather than enforcing a strict 5% share; adding one heavy question would make the
   percentage literal.
4. Debate is represented by a single question (the country song). Sparing was the rule,
   absent was not the intent. Add 6-8 debate pairs later if the mode feels flat.

## Gotchas that cost time last session

- Author CSS with `display: flex` beats the `hidden` attribute, so both sheets were
  invisible but swallowing every tap. `[hidden] { display: none !important; }` in
  `styles.css` must stay.
- Light-mode muted text measured 4.29:1; `--muted` is `#665c54` for that reason. Do not
  lighten it.
- Filter chips: when a group is empty (= all), tapping one chip narrows to just that
  chip. Every group also gets an explicit `All` chip. This was a real bug once.
- The "All" chip looked selected in screenshots because the sheet focused its first
  button. Sheets now focus the dialog itself.
- Validator runs are the cheapest safety net: run it after every content edit, it prints
  distributions and writes the review page.
- `.hermes/` is gitignored, so the plan is not in git. If this machine dies, the plan
  dies with it. Worth copying into `docs/` if you want it durable.

## Session-start checklist

1. Read this file, then the plan at `.hermes/plans/2026-10-17_174723-katchup-three-modes.md`.
2. `cd ~/Git/katchup && git log --oneline -3 && git status --short` — the tree should be
   clean apart from ignored files.
3. `python3 scripts/validate_questions.py` — expect exit 0.
4. Start the dev server on 8099 if it is not up.
5. Decide: Phase 1 (validators and schema) or fix the era chips first. Phase 1 is the
   plan's order; the era chips are a five-minute detour if it annoys you.

## Non-goals, still

No accounts, no sync, no backend, no analytics, no answer logging, no sharing, no
sharing cards, no scores, no monetization, no offline mode, no AI at runtime.
