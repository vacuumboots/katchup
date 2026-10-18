# katchup — handoff

Written 2026-10-17 at the end of a long session, updated the same day after phases 1
and 2 landed. Read this first, then the plan it points at. Five minutes to productive.

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

- **309 questions**, all validated: 203 light / 91 medium / 15 heavy. `validate_questions.py`
  exits 0, no errors, no warnings. Unchanged by the three-mode work.
- **Phase 1 done:** `scripts/validate_wyr.py`, `scripts/validate_categories.py`,
  `scripts/validate_all.sh`, plus `scripts/test_validators.sh` (40 checks against broken
  fixtures) and the two content stubs — `wouldrather.json` with 6 real pairs,
  `categories.json` with 1 complete 14-item deck (sandwiches). The categories stub fails
  on the count rules, which is the intended state.
- **Phase 2 done:** `app.js` is gone, split into `app-core.js` (router, screens, sheets,
  chips, storage, JSON cache) and `app-open.js` (the whole existing mode, moved not
  rewritten). `index.html` now holds six `<section class="screen">` blocks. The mode
  picker is live.
- **Phase 3 done:** `wouldrather.json` is the full **200 pairs** (140 light / 60 medium,
  13 topics at 8+, 72% dilemma) and `app-random.js` plays them: shuffled pool from this
  mode's own filters, pick / skip / one-level undo, live count, empty and done states.
  Choices are 96px with 20px text, dropping to 17px rather than clipping.
- **Headless suite: 76/76 checks pass** at 375x667, home + open + random + routing, plus
  a 390x844 fit check. Zero console errors, zero network requests after load.
- Ten commits on `main`. Tree clean; `review*.html` and `.hermes/` are ignored.
- Dev server was restarted on <http://127.0.0.1:8099> at handoff. If it is dead:
  `python3 -m http.server 8099` from the repo root.

What ships today: a home screen with three cards, Open ended and Would you rather
random both playable, Categories still a placeholder. Home shows live counts for open
ended ("N questions left in this filter") and random ("N pairs"); the categories count
line is blank until Phase 4 registers one.

## The work in flight: three game modes

1. **Open ended** — done, behind `#open`.
2. **Would you rather random** — dilemma pairs, two options, pick one, next.
3. **Would you rather Categories** — a category deck where the winner stays on and
   faces the next item until one champion is left.

**The plan is on disk at `.hermes/plans/2026-10-17_174723-katchup-three-modes.md`.** It is
deliberately gitignored (`.hermes/` in `.gitignore`), so it does not travel with the repo,
only with this machine. Read it before touching code: screen specs, data schemas, route
names, state shapes, validator rules, build order, verification steps.

### Decisions already locked (do not re-litigate)

- Mode labels: `Open ended`, `Would you rather random`, `Would you rather Categories`.
- Routes: `#`, `#open`, `#random`, `#categories`, `#categories/<id>`,
  `#categories/<id>/done`.
- **No sessions.** Every entry starts fresh. Nothing resumes or expires. Repeats across
  visits are fine because one tap skips. Persisted state is only the open-ended deck's
  asked/never/history, plus two independent filter sets.
- **No scoring.** No points, streaks, or pick history.
- Filters exist in both question modes, with **independent settings**; the random mode
  stores only `katchup_random_v1` = its filters.
- Content is generic for **Canada and the US**. No local decks, no single-country chains.
- **Tone line for would-you-rather: death and loss are out.** Nothing about dying,
  killing, funerals, grief, or losing a person. Injuries and mishaps are allowed and
  wanted, 5-10 of the 200 pairs, nothing past a black eye or a broken arm.
- Category count: **12 decks**, 14 items each. Music artists stays one mixed-era deck
  for now; splitting it is a later one-file change that would make it 13.

### Next step: Phase 4 — would you rather Categories

1. **Content:** grow `categories.json` from 1 deck to 12, 14 items each (168 items), one
   deck at a time, running `python3 scripts/validate_categories.py` after each and
   reading `review_categories.html` for "would anybody defend this item". The ten decks
   still to write: pizza toppings, fast food places, breakfast, desserts, road trip
   snacks, vacation spots, cities, music artists, TV shows, board games, seasons.
   Sandwiches is already done and is the shape to copy.
2. **Code:** `app-categories.js` (picker, bracket, champion, undo, restart) registering
   `Katchup.registerMode("categories", { enter })` and a count provider. Two new routes
   have to be added to `app-core.js`: `#categories/<id>` and `#categories/<id>/done`, in
   the same `routes` table, since only `#categories` exists today. Content comes from
   `Katchup.fetchJSON("categories", "categories.json")`.

Verify: a 14-item deck produces exactly 13 duels and one champion; the champion screen
lists the 13 beaten items in order; undo rewinds one duel and restores the loser; entering
the category again reshuffles and starts at duel 1. Then Phase 5: polish, a11y pass,
README/spec, deploy, live verification.

## Commands

```sh
cd ~/Git/katchup

# local server (leave running in a background terminal)
python3 -m http.server 8099

# content gates
python3 scripts/validate_questions.py     # also writes review.html
bash scripts/validate_all.sh              # all three files, exits 1 until content lands
bash scripts/test_validators.sh           # proves each validator rule actually fires

# headless regression run (see harness below)
cd ~/.hermes/cache/scratch/katchup-test && node test.js

# ship: Pages rebuilds on push to main
git add -A && git commit -m "..." && git push origin main

# confirm the deploy actually rebuilt, not just that the push worked
gh api repos/vacuumboots/katchup/pages --jq .status    # wait for "built"
curl -s https://vacuumboots.github.io/katchup/questions.json | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
```

`gh` is authenticated as `vacuumboots` with `repo` scope. Pages is served from `main`,
root path, with `.nojekyll` in place. The first build after adding Pages errored once
and the rebuild came back clean, so a single `errored` status is not necessarily fatal.

Nothing is deployed since the split: `main` is ahead of the live site. Deploy at the end
of a phase, not mid-split, or the live site breaks.

## Verification harness

No test suite in the repo. The checks live in a scratch directory on this machine, using
puppeteer-core pointed at the Playwright chromium that is already downloaded:

- Scripts: `~/.hermes/cache/scratch/katchup-test/` — `test.js` is the main one (45
  checks, exits non-zero on failure, prints JSON with a `failures` array); `verify.js`
  does worst-case layout, `contrast.js` does colour ratios, `shots.js` and `live.js` do
  screenshots and the deployed-site check.
- Browser: `~/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell`
- Run: `cd ~/.hermes/cache/scratch/katchup-test && node test.js`
- Note: the browser tool refuses localhost URLs, which is why this is puppeteer over the
  CLI instead.

`test.js` covers, in order: home layout (three 112px cards, live counts, no scroll),
routing to `#open`, ← Modes present at 44px, question font 28px, no layout scroll,
three actions inside the bottom quarter, ask three / undo restores the card and drops it
from `asked`, skip, never and their undo, follow-ups toggle, era chips include `midlife`
and drop `family`, filtering to heavy with an accurate count, reload keeps asked/never
and the current card and stays on `#open`, empty state, export/import round trip,
no network requests after load, ← Modes returns home, unknown hash falls back home, then
the whole random mode (ten distinct pairs, 11 of 200, undo, skip, filter counts n
independent of open's, reload restarts the run but keeps filters, home count), the empty
state, the done state, and the longest authored side rendering unclipped — the last three
driven by a one-pair stub deck served through request interception on a second page, then
a 390x844 fit check.

Extend it as modes land. When the new modes are in, copy it into `scripts/` as a
committed smoke test (it will need `NODE_PATH` set to the scratch `node_modules`).

## Code map

```
index.html            six screens as sections, shared header, three sheets
app-core.js           227 lines: storage, JSON cache, fade, sheets, chips,
                      registerMode/registerCount, hash router, home painting
app-open.js           565 lines: everything the app used to do, moved into an IIFE
app-random.js         323 lines: pair pool, shuffle, pick/skip/undo, its own filters
styles.css            gruvbox light/dark, 76px actions, 96px choices, [hidden] override
questions.json        309 questions, the deck
wouldrather.json      200 pairs, 140 light / 60 medium
categories.json       STUB: 1 complete deck, sandwiches, 14 items
scripts/validate_questions.py    validator + review.html emitter (449 lines)
scripts/validate_wyr.py          pairs + review_wyr.html (373 lines)
scripts/validate_categories.py   decks + review_categories.html (311 lines)
scripts/validate_all.sh          runs all three, one summary line
scripts/test_validators.sh       40 assertions against fixtures/
scripts/fixtures/                deliberately broken content, for the tests above
manifest.webmanifest  home-screen shortcut only
icons/                192 and 512 placeholder PNGs
mvpspec.md            the brief, amended
```

`app-core.js` anchors: `readStore` 21, `writeStore` 29, `fetchJSON` 43, `fadeTo` 65,
`openSheet` 79, `closeSheets` 88, `makeChip` 106, `registerMode` 118, `registerCount` 122,
`show` 130, `paintHome` 146, `enterMode` 158, `render` 168, `start` 183.

`app-open.js` anchors: `defaultState` 67, `migrate` 80, `pickNext` 153, `showCard` 174,
`advance` 222, `act` 238, `undo` 259, `renderFilters` 292, `enter` 432, `wire` 464.

`app-random.js` anchors: `readPrefs` 56, `ensureDeck` 77, `buildOrder` 103, `render` 119,
`pick` 176, `undo` 183, `skip` 191, `renderFilters` 202, `wire` 272, `enter` 298.

How a mode plugs in: the mode's file calls `Katchup.registerMode(name, { enter })` and
`Katchup.registerCount(name, async () => "…")` at load. The router shows the screen and
awaits `enter`. Nothing else in core knows about any mode. Content is fetched through
`Katchup.fetchJSON(key, url)`, which caches the promise so two callers share one request
and a failure clears the cache for a retry.

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

Would-you-rather (validated, content not written): `a`/`b` 3-60 chars, no end punctuation,
no question mark, must not repeat "Would you rather", same grammatical shape both sides
(warned, not failed), light or medium only, no duplicate pair in either direction,
death/loss blocklist as errors, politics/religion/money-status as warnings. Review page is
the gate for "obviously better".

Categories (validated, one deck written): kebab-case ids, 12-20 items per deck (target 14),
labels unique ignoring case and punctuation, near-duplicate labels over 50% Jaccard fail,
label 40 chars, blurb 12 words, prompt ends in `?` and under 40 chars, 12 decks minimum.

## Known issues / deliberately deferred

1. **"Back" and "← Modes" sit in the same header row** on the open screen, and "Back"
   there means undo, not navigation. The aria-label already says "Undo last action", but
   the visible word is ambiguous now that ← Modes exists. Candidate rename in Phase 5
   (to "Undo"), not done here because the plan locks the open-ended screen as unchanged.
2. **The categories count line on home is blank** until Phase 4 registers a provider. The
   line reserves its height, so nothing jumps.
3. **`bash scripts/validate_all.sh` exits 1 right now**, by design: `categories.json` is
   still a one-deck stub and fails the count rule. The fixture tests assert it fails for
   the right reasons.
4. `review.html`, `review_wyr.html`, `review_categories.html` are gitignored; regenerate
   rather than commit them.
5. Heavy is 15 questions = 4.9% of 309. The validator floors at 15 questions and caps at
   10% rather than enforcing a strict 5% share; adding one heavy question would make the
   percentage literal.
6. Debate is represented by a single question (the country song). Sparing was the rule,
   absent was not the intent. Add 6-8 debate pairs later if the mode feels flat.
7. **Nothing since the split is deployed.** `main` is 2 commits ahead of the live site.

## Gotchas that cost time

- Author CSS with `display: flex` beats the `hidden` attribute, so both sheets were
  invisible but swallowing every tap. `[hidden] { display: none !important; }` in
  `styles.css` must stay. The same rule is what makes `.screen` switching work.
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
- **The dev server wedges.** A `python3 -m http.server` that is still listening can return
  an empty reply (curl: `Empty reply from server`, puppeteer: `ERR_EMPTY_RESPONSE`).
  Kill it, start a fresh one, and curl `/index.html` before blaming the app.
- **Stub content in the harness needs `setRequestInterception` + `setCacheEnabled(false)`
  on that page, armed before its first navigation.** `evaluateOnNewDocument` silently did
  not run, and without cache disabled Chromium served the real JSON from disk cache, so
  the "empty state" test quietly ran against the 200-pair deck and passed nothing.
  Verify a stub by asserting the served pair's text, not just that a card appeared.
- **The harness must navigate with `#open`.** Home is the entry point now, so a bare
  `index.html` load lands on the mode picker and every `#question` wait times out.
- `node --check` on the three app files is a two-second syntax gate before the browser run.
- Home counts paint asynchronously; tests must `waitForFunction` on the count text rather
  than sleeping.
- The random pair card starts `hidden` in the markup and is only unhidden by `render()`,
  so a test that samples too early sees a blank screen, not an empty pair.

## Session-start checklist

1. Read this file, then the plan at `.hermes/plans/2026-10-17_174723-katchup-three-modes.md`.
2. `cd ~/Git/katchup && git log --oneline -3 && git status --short` — clean apart from
   ignored files.
3. `python3 scripts/validate_questions.py` — expect exit 0.
   `bash scripts/test_validators.sh` — expect 40/40.
4. Dev server on 8099: curl it, do not assume. Restart if the reply is empty.
5. `cd ~/.hermes/cache/scratch/katchup-test && node test.js` — expect 76/76 before you
   change anything. That is your baseline.
6. Then Phase 4: content first (one deck at a time, validate each), code second.

## Non-goals, still

No accounts, no sync, no backend, no analytics, no answer logging, no sharing, no
sharing cards, no scores, no monetization, no offline mode, no AI at runtime.
