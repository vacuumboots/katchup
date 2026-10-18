# katchup — handoff

Written 2026-10-17 at the end of a long session, updated the same day after phases 1, 2,
3, 4 and the phase 5 polish pass landed. Read this first, then the plan it points at.
Five minutes to productive.

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

- **329 questions**, all validated: 220 light / 94 medium / 15 heavy. `validate_questions.py`
  exits 0, no errors, no warnings. Unchanged by the three-mode work.
- **Phase 1 done:** `scripts/validate_wyr.py`, `scripts/validate_categories.py`,
  `scripts/validate_all.sh`, plus `scripts/test_validators.sh` (42 checks against broken
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
- **Phase 4 done:** `categories.json` was 13 decks of 14 (182 items) and
  `app-categories.js` plays a bracket: picker with Play at random, champion on top,
  challenger below, duel N of 13, one-level undo, restart, champion trail, play again.
  Routes `#categories/<id>` and `#categories/<id>/done` are live.
- **Headless suite: 109/109 checks pass** at 375x667, home + open + random + categories +
  routing + the accessibility pass + the 40-deck picker and its jump chips, plus a 390x844
  fit check. Zero console errors, zero network requests after load.
  `bash scripts/validate_all.sh` exits 0.
- **Phase 5 done.** Focus moves on every screen swap (each `.screen` has `tabindex="-1"`
  and an `aria-label`; `show()` in `app-core.js` focuses it with `preventScroll`), the
  three undo buttons now read "Undo" instead of "Back", and the champion trail counter
  no longer uses `opacity: 0.7` — that dropped it to 3.04:1 light / 3.61:1 dark, so it is
  now 13px full-strength `--muted` at 5.74:1 / 5.90:1.
- Fourteen commits on `main`. Tree clean; `review*.html` and `.hermes/` are ignored.
- **Content pass, same day:** Categories went from 13 decks to **40** (27 authored, 560
  items, 8 themes) and **50 of the questions were rewritten** — every "Tell me about…"
  imperative and every "Which thing did you…" template is gone, and the abstract prompts
  ("what do you do that makes the time disappear?", "when did you feel properly grown up?")
  were replaced with concrete asks.
- **Read-through pass, same day (after warmth):** yes, the deck was read end to end
  again, and it was worth it — three collision clusters and five vague leftovers had
  survived both earlier passes. Fixed: `q0007` (three "first earnings" cards), `q0252`
  (two sick-day cards once `q0336` landed), `q0329` (duplicate of `q0286`), plus
  `q0004`, `q0015`, `q0034`, `q0083`, `q0098` rewritten from vague to concrete. Counts,
  weights and caps unchanged.
- **Warmth pass, same day:** the deck is a gift between family members, and the sharpening
  pass had made it colder — it asked for facts and named almost nobody. Fixed by adding
  **20 cards that are warm by construction** (gratitude, inherited habits, small kindnesses,
  handwriting, being looked after) and rewriting **20 existing cards to name a person**
  ("What was the meal you asked for on your birthday?" became "Which birthday meal did you
  ask your mother for?"). Cards naming a family member went 33 → 70 (21%), and 14 more
  quiz-style follow-ups ("Who defended you?", "What gave it away?") became invitations
  ("What did they say after?", "How long before someone noticed?"). Deck is now **329**
  (220 light / 94 medium / 15 heavy); `TARGET_*` in the validator carries those numbers and
  the report prints a Warmth line so the next content pass cannot quietly undo it.
- **The live site matches `main` byte for byte** — verified 2026-10-17 by hashing all nine
  shipped files against https://vacuumboots.github.io/katchup/. Pages status `built`.
  Deploy at the end of a phase, as before.
- Dev server was restarted on <http://127.0.0.1:8099> at handoff. If it is dead:
  `python3 -m http.server 8099` from the repo root.

What ships today: all three modes are playable, each behind one tap from the home screen,
with a live count on every card. The live site carries all of it — the three-mode build
plus the Books deck — and matches `main` exactly.

**All five phases are done.** What is left is optional content work and the deferred
items in "Known issues", not missing features.

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
- Category count: **40 decks**, 14 items each, 560 items, grouped into 8 themes
  (`group` field). The validator treats 12 as a floor, never an exact target, so decks can
  be added freely. The plan's original 12 became 13 when **Books** was added, then 40 in
  the content pass of 2026-10-17. Music artists still stays one mixed-era deck.

### Phase 5, done

The polish pass landed on 2026-10-17. All three items, verified in the headless suite:

1. **Accessibility.** Every `.screen` now has `tabindex="-1"` and an `aria-label`
   ("Mode picker", "Open ended", "Would you rather random", "Would you rather Categories",
   "Category duel", "Champion"), and `show()` in `app-core.js` moves focus onto the
   screen it just revealed, with `preventScroll`. `.screen:focus` has its outline
   suppressed the same way `.sheet` does. Confirmed by keyboard smoke: Tab from the
   focused screen reaches Follow-ups → Asked it → Skip → Never → ← Modes, no hidden
   stops, and "u" still undoes. Worth knowing: the old symptom was focus falling to
   `BODY` (the browser drops focus when the activated node is hidden), not focus sitting
   inside a hidden element.
2. **"Back" is now "Undo"** in all three places (`undoBtn`, `randomUndoBtn`,
   `duelUndoBtn`). `undoBtn` keeps `aria-label="Undo last action"`; the visible word is
   contained in the accessible name, so label-in-name still holds.
3. **Trail contrast.** `.trail-duel` was `opacity: 0.7`, which blends `--muted` toward
   the card: 3.04:1 light, 3.61:1 dark. Opacity is gone; the counter is 13px
   full-strength `--muted` with tabular numerals, 5.74:1 / 5.90:1. Size, not alpha, does
   the de-emphasis.

### Next, if it is ever picked up again

Nothing is queued. The candidates, in rough order of value:

1. Copy the headless suite into `scripts/` if you want CI-able verification in-repo. It
   is 800 lines and needs `NODE_PATH` pointing at the scratch `node_modules`, so it is
   not free — that is why it is still out-of-repo.
2. Add 6-8 debate-flavoured pairs (see Known issues 5).
3. Copy this handoff's plan (`.hermes/plans/…`, gitignored) into `docs/` so it survives
   this machine.

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

`main` and the live site are in sync (checked by hashing the deployed files, not by eye).
Deploy at the end of a phase, not mid-split, or the live site breaks mid-refactor.

## Verification harness

No test suite in the repo. The checks live in a scratch directory on this machine, using
puppeteer-core pointed at the Playwright chromium that is already downloaded:

- Scripts: `~/.hermes/cache/scratch/katchup-test/` — `test.js` is the main one (105
  checks, exits non-zero on failure, prints JSON with a `failures` array); `verify.js`
  does worst-case layout, `contrast.js` does colour ratios, `contrast-trail.js` measures
  the champion trail in both colour schemes, `keyboard-smoke.js` walks Tab order and the
  "u" undo shortcut, `falsify-focus.js` re-runs the focus assertion against a doctored
  `app-core.js` (served by request interception) to prove the check actually bites, and
  `shots.js` / `live.js` do screenshots and the deployed-site check.
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
the categories mode (forty picker rows at 76px in eight theme groups with matching jump
chips, a chip scrolling its group to the top, duel 1 of 13, undo rewinding one duel,
restart, a full 13-duel run, a 13-item unique trail, the champion route, Play again,
Another category, a stale champion URL falling back to duel 1, and the home count), then
the accessibility pass (focus on home at load, focus following the swap into open, random
and champion, no focus left inside `[hidden]`, the three buttons reading "Undo", and the
trail counter's measured ratio ≥ 4.5), then a 390x844 fit check.

Extend it as modes land. When the new modes are in, copy it into `scripts/` as a
committed smoke test (it will need `NODE_PATH` set to the scratch `node_modules`).

## Code map

```
index.html            six screens as sections (each tabindex -1 + labelled),
                      shared header, three sheets
app-core.js           244 lines: storage, JSON cache, fade, sheets, chips,
                      registerMode/registerCount, hash router (focuses the
                      screen it reveals), home painting
app-open.js           565 lines: everything the app used to do, moved into an IIFE
app-random.js         323 lines: pair pool, shuffle, pick/skip/undo, its own filters
app-categories.js     347 lines: grouped picker with jump chips, bracket, champion,
                      restart, play at random
styles.css            gruvbox light/dark, 76px actions, 96px choices, [hidden] override
questions.json        329 questions, the deck
wouldrather.json      200 pairs, 140 light / 60 medium
categories.json       40 decks, 14 items each, 560 items, 8 theme groups
scripts/validate_questions.py    validator + review.html emitter (449 lines)
scripts/validate_wyr.py          pairs + review_wyr.html (373 lines)
scripts/validate_categories.py   decks + review_categories.html (311 lines)
scripts/validate_all.sh          runs all three, one summary line
scripts/test_validators.sh       42 assertions against fixtures/
scripts/fixtures/                deliberately broken content, for the tests above
manifest.webmanifest  home-screen shortcut only
icons/                192 and 512 placeholder PNGs
mvpspec.md            the brief, amended
```

`app-core.js` anchors: `readStore` 21, `writeStore` 29, `fetchJSON` 43, `fadeTo` 65,
`openSheet` 79, `closeSheets` 88, `makeChip` 106, `registerMode` 118, `registerCount` 122,
`show` 130 (focus move at 147), `isScreen` 151, `paintHome` 155, `enterMode` 167,
`render` 183, `start` 198.

`app-open.js` anchors: `defaultState` 67, `migrate` 80, `pickNext` 153, `showCard` 174,
`advance` 222, `act` 238, `undo` 259, `renderFilters` 292, `enter` 432, `wire` 464.

`app-random.js` anchors: `readPrefs` 56, `ensureDeck` 77, `buildOrder` 103, `render` 119,
`pick` 176, `undo` 183, `skip` 191, `renderFilters` 202, `wire` 272, `enter` 298.

`app-categories.js` anchors: `slug` 71, `renderPicker` 77 (builds theme blocks and jump
chips), `start` 143, `renderDuel` 173, `pick` 190, `undo` 212, `finish` 221,
`renderChampion` 230, `enter` 251, `duel` 265, `done` 285, `wire` 315.

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
- **Warmth is a content rule, not a mood.** This deck exists so a family can talk, so a
  card that only extracts a fact is a bad card. Name the person when the card is about one
  ("your mother", "your father", "your grandmother"); prefer follow-ups that invite detail
  ("What did they say after?", "How did they do it without being asked?") over ones that
  close the floor ("Who defended you?", "What gave it away?"); and write cards the other
  person wants to answer. Cards q0321-q0340 are the reference set — gratitude, inherited
  habits, being looked after. The validator prints warmth as a number and never fails on
  it; watch it, do not game it.
- **Never open with "Tell me about"** or "Which thing did you…". Both were in the deck and
  both read as a form to fill in rather than a question. A card gets one ask, a concrete
  anchor (an object, a number, a place, a named person), and nothing that invites "not
  much". The 2026-10-17 pass rewrote 50 cards against this rule; the review page is still
  the human gate for whether the story is worth asking for.
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

Would-you-rather (validated, 200 pairs written): `a`/`b` 3-60 chars, no end punctuation,
no question mark, must not repeat "Would you rather", same grammatical shape both sides
(warned, not failed), light or medium only, no duplicate pair in either direction,
death/loss blocklist as errors, politics/religion/money-status as warnings. Review page is
the gate for "obviously better".

Categories (validated, 40 decks written): kebab-case ids, 12-20 items per deck (target 14),
labels unique ignoring case and punctuation, near-duplicate labels over 50% Jaccard fail,
label 40 chars, blurb 12 words, prompt ends in `?` and under 40 chars, 12 decks minimum.

Decks also carry a `group` (one of 8 themes) that the picker renders as a heading with a
sticky jump chip. The prompt is the question the bracket answers, so write it as one
(`Which pie gets the fork?`, not `Pies`). The blurb is where the joke goes: concrete,
under 12 words, never a restatement of the label. Decks must be playable by someone who
has never seen the list, so no hyper-local items and nothing that needs a footnote.

## Known issues / deliberately deferred

1. ~~"Back" and "← Modes" in the same header row~~ — **fixed in Phase 5**: all three
   undo buttons read "Undo".
2. ~~No focus management on screen swaps~~ — **fixed in Phase 5**: `show()` focuses the
   revealed screen. If you add a screen, give its `<section class="screen">` a
   `tabindex="-1"` and an `aria-label`, or it will not be focusable and the swap will
   fall back to `BODY`.
3. `review.html`, `review_wyr.html`, `review_categories.html` are gitignored; regenerate
   rather than commit them.
4. Heavy is 15 questions = 4.6% of 329. The validator floors at 15 questions and caps at
   10% rather than enforcing a strict 5% share; adding one heavy question would make the
   percentage literal.
5. Debate is represented by a single question (the country song). Sparing was the rule,
   absent was not the intent. Add 6-8 debate pairs later if the mode feels flat.
6. ~~Nothing since the split is deployed~~ — **resolved**: the live site matches `main`.

## Gotchas that cost time

- Author CSS with `display: flex` beats the `hidden` attribute, so both sheets were
  invisible but swallowing every tap. `[hidden] { display: none !important; }` in
  `styles.css` must stay. The same rule is what makes `.screen` switching work.
- Light-mode muted text measured 4.29:1 against the body background but 5.74:1 against
  the card (`--muted` is `#665c54`); measure against the element's real painted
  background, not `body`. Do not lighten it.
- **A near-duplicate scan cannot see two cards that ask the same thing in different
  words.** `q0329` ("Who taught you something you still use every week?") and `q0286`
  ("Which skill did a relative teach you that you still use?") share only ~30% of their
  words, so neither the validator nor a 45% Jaccard sweep flags them. Only reading the
  deck catches that class. After any two overlapping content passes, read it end to end
  before shipping — the 2026-10-18 read found three such clusters.
- **The two-word opener cap is a live constraint.** `What did` sits at 13.7% against a 15%
  cap, so almost any new card of that shape pushes the deck over. Check
  `python3 scripts/validate_questions.py` after adding cards and vary the opener (Which /
  Whose / How did / What was) before adding volume.
- **Never dim text with `opacity`** here: alpha blends toward the background and silently
  breaks contrast (`opacity: 0.7` on the trail counter cost 2.7 points of ratio). Use
  size, weight or spacing to de-emphasise.
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
  Kill it, start a fresh one, and curl `/index.html` before blaming the app. It can also
  wedge *and stay bound*: on 2026-10-17 a dead server held `127.0.0.1:8099` (IPv4) while a
  fresh one bound `*:8099` (IPv6), so `curl 127.0.0.1:8099` kept hitting the corpse and
  every test failed at `goto`. Check with `lsof -nP -iTCP:8099 -sTCP:LISTEN` — if you see
  two PIDs, kill the IPv4 one. The port looking "listening" proves nothing.
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
- **`padding-top` on a scroll container leaves a band above a sticky child.** The picker's
  jump bar is `position: sticky` inside `main.stage-scroll`; while `.stage` padded it 8px,
  scrolled deck rows showed through that strip above the bar (smeared letters, looks
  broken). `.stage-scroll` now has `padding-top: 0` and the bar carries its own 8px. If you
  add padding back, the band returns — `test.js` asserts the bar's top equals the
  scroller's top while stuck.
- **New CSS goes at the END of `styles.css`.** `.stage` and `.card` live at line ~150 with
  single-class specificity; a block appended before them loses every tie silently. That is
  exactly how the category picker ended up vertically centred with its first rows above
  the viewport. The would-you-rather and categories blocks now sit at the end of the file.
- A full-screen picker is allowed to scroll; the no-scroll invariant covers home, random,
  duel and champion only.

## Session-start checklist

1. Read this file, then the plan at `.hermes/plans/2026-10-17_174723-katchup-three-modes.md`.
2. `cd ~/Git/katchup && git log --oneline -3 && git status --short` — clean apart from
   ignored files.
3. `bash scripts/validate_all.sh` — expect all three green.
   `bash scripts/test_validators.sh` — expect 42/42.
4. Dev server on 8099: curl it, do not assume. Restart if the reply is empty.
5. `cd ~/.hermes/cache/scratch/katchup-test && node test.js` — expect 109/109 before you
   change anything. That is your baseline.
6. Everything is built and shipped. Pick up from "Next, if it is ever picked up again",
   or from Known issues.

## Non-goals, still

No accounts, no sync, no backend, no analytics, no answer logging, no sharing, no
sharing cards, no scores, no monetization, no offline mode, no AI at runtime.
