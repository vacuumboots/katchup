# katchup

One good conversation question at a time. A phone-first static page for when you
are sitting with someone you know well and the conversation has stalled.

Live: <https://vacuumboots.github.io/katchup/>

309 questions, written by hand, tagged by era, topic, weight, kind, and hook. One card
on screen, three buttons: **Asked it**, **Skip**, **Never**. **Back** undoes the
last action. Follow-up prompts are one tap away if the answer starts a story.

The home screen offers three modes: **Open ended** (the deck above), **Would you
rather random** (200 dilemma pairs, pick one and move on), and **Would you rather
Categories** (pick a deck, two items go head to head, the winner stays on until one
champion is left).

No accounts, no backend, no analytics, no network calls after the page loads.

## Routes

Hash routing, no library, so browser back works and every screen is linkable.

`#` home · `#open` open ended · `#random` would you rather · `#categories` category
picker · `#categories/<id>` a duel in that deck · `#categories/<id>/done` the champion.

## Run it locally

```sh
python3 -m http.server 8099
```

Then open <http://127.0.0.1:8099/>. A plain `file://` load also works in most
browsers, but the local server is closer to what a host will serve.

## Deploy

The whole app is static: `index.html`, `app-core.js`, `app-open.js`, `app-random.js`,
`app-categories.js`, `styles.css`, `questions.json`, `wouldrather.json`, `categories.json`,
`manifest.webmanifest`, and `icons/`. Any static host will do. Serve over HTTPS if you
want "Add to Home Screen" to give you a proper shortcut.

- **GitHub Pages**: push the repo, then Settings -> Pages -> Deploy from branch,
  root folder. The site lands on the repo URL.
- **Netlify**: drag the folder into the dashboard, or point a site at the repo
  with no build command and publish directory `.`.
- **nginx**: copy the files into a directory and serve it. Add
  `types { }` nothing special; the defaults handle `.webmanifest` fine on modern
  nginx. If yours does not, add
  `location = /manifest.webmanifest { default_type application/manifest+json; }`.

There is no build step and nothing to compile.

## Adding or editing questions

All content lives in `questions.json`, a flat array:

```json
{
  "id": "q0001",
  "text": "Tell me about the kitchen you grew up in?",
  "era": "childhood",
  "topic": "home",
  "weight": "light",
  "kind": "memory",
  "hook": "scene",
  "followups": ["Where did everyone sit?", "What was always on the counter?"]
}
```

- `id`: `qNNNN`, unique and never reused. Append with the next free number.
  Deleted ids are never recycled.
- `era`: `childhood` `teens` `young-adult` `career` `midlife` `now`. Tag it by
  when the remembered event happened; present-tense questions are `now`.
- `topic`: `music` `food` `cars` `work` `school` `places` `home` `firsts`
  `people` `money` `hobbies` `media` `advice`
- `weight`: `light` (fine to ask cold) `medium` `heavy` (regret, loss, the
  relationship itself). Heavy is hidden by default.
- `kind`: `memory` `opinion` `hypothetical`
- `hook`: the mechanism the question trades on. `extreme` and `measure` ask for a
  superlative or a number (longest, furthest, how many), and the number pulls the
  story out. `artifact` asks about a specific object. `relational` is about a
  person. `scene` asks you to stand somewhere again. `debate` is an opinion people
  will defend, tagged and kept rare because it plays better in groups than one to
  one. `plain` is everything else.
  Caps the validator enforces: extreme + measure + artifact + relational + scene at
  40 percent or more of the deck, extreme + measure at 10 percent or more, debate
  at 5 percent or less, and "favourite" questions at 5 percent or less (only use
  one when everyone has an opinion on the thing, or when a story comes attached).
- `followups`: 1 to 3 prompts, each ending in a question mark.

Then run the validators:

```sh
python3 scripts/validate_questions.py     # this deck only
bash scripts/validate_all.sh              # all three content files
```

It checks ids, enum values, follow-up counts, question marks, yes/no openers,
duplicates, and near-duplicates, prints the distributions against the spec
targets, and exits non-zero on hard errors. Passing it proves the deck's shape,
not its quality: it also writes `review.html`, one page with every question, for
a read-through. `bash scripts/test_validators.sh` proves the validators still
fail on the rules they claim to enforce.

## Adding or editing would-you-rather pairs

`wouldrather.json` is a flat array of pairs. The UI supplies the words "would you
rather":

```json
{
  "id": "w0001",
  "a": "Never wait in a line again",
  "b": "Never sit in traffic again",
  "topic": "advice",
  "weight": "light",
  "kind": "dilemma"
}
```

- `id`: `wNNNN`, unique and never reused.
- `a`, `b`: one short phrase each, 3 to 60 characters, no end punctuation, and the
  same grammatical shape on both sides. Do not write "Would you rather" in either.
- `topic`: the same list as the question deck, so the chips match.
- `weight`: `light` or `medium`. There is no heavy tier here.
- `kind`: `dilemma` (trade one annoyance for another), `preference` (which is
  better), `impossible` (absurd but harmless).

One hard rule: **no death and no loss of a person.** Nothing about dying, killing,
funerals, grief, or losing someone. Injuries and mishaps are wanted. `python3
scripts/validate_wyr.py` enforces the shape, the duplicates, and the death wording,
and writes `review_wyr.html`, which is the real gate: for every pair, ask whether
one side is obviously better and whether it lands badly at a family table.

## Adding or editing category decks

`categories.json` is an array of decks. One deck is one bracket:

```json
{
  "id": "sandwiches",
  "name": "Sandwiches",
  "prompt": "Which sandwich?",
  "items": [
    { "id": "tuna-salad", "label": "Tuna salad" },
    { "id": "reuben", "label": "Reuben", "blurb": "corned beef, kraut, Russian dressing" }
  ]
}
```

- `id`: kebab-case, unique across decks. It is also the URL: `#categories/<id>`.
- `name`: up to 20 characters, shown on the picker row and in the duel header.
- `prompt`: ends in `?`, under 40 characters. The question every duel asks.
- `items`: 12 to 20 per deck (14 is the house number). Under 12 the bracket ends
  too fast; over 20 it drags.
- `label`: up to 40 characters, unique within the deck ignoring case and
  punctuation. `blurb` is optional, 12 words at most.

`python3 scripts/validate_categories.py` enforces all of that, plus duplicate ids,
near-duplicate labels (50% word overlap), and the 12-deck minimum, and writes
`review_categories.html`. That page is the real gate: an item nobody would defend is
a dud, and a deck of near-synonyms has no duels in it.

## What is stored, and where

Everything lives in `localStorage` under `katchup_state_v1`: which ids have been
asked or never asked again, the current card, this session's skips, your filter
selection, and a timestamped history of asks.

Would you rather random keeps exactly one thing of its own, `katchup_random_v1`,
and it is only a preference: its topic and weight chips. No pair, no picks, no
counters. Every visit shuffles a fresh run, which is why nothing needs clearing.
Category mode stores nothing at all; the bracket lives in memory for the visit.

There is no sync and no server. **Stats -> Export history** downloads the state
as JSON; **Import history** loads it back into a cleared browser. That is the
only backup path.

## Keyboard

Arrow left skips, arrow right marks asked, `n` marks never, `Backspace` or `u`
undoes. Escape closes a sheet. Swiping the card does skip and asked, but the
buttons are always the primary path.

## Files

```
index.html              six screens as sections, plus the shared header and three sheets
app-core.js             state storage, hash router, screen show/hide, sheets, chips
app-open.js             open ended: selection, undo, filters, stats, export/import
app-random.js           would you rather: shuffled pool, pick, skip, undo, filters
app-categories.js       categories: picker, bracket, champion, restart
styles.css              gruvbox light and dark, system font stack
questions.json          the deck
wouldrather.json        the 200 pairs
categories.json         the 12 decks, 14 items each
manifest.webmanifest    home screen shortcut (no service worker, so no offline)
icons/                  placeholder PNGs, 192 and 512
scripts/validate_questions.py    question validator and review.html generator
scripts/validate_wyr.py          pair validator and review_wyr.html generator
scripts/validate_categories.py   deck validator and review_categories.html generator
scripts/validate_all.sh          runs all three
scripts/test_validators.sh       proves each validator rule actually fires
```
