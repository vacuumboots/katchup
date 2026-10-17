# katchup

One good conversation question at a time. A phone-first static page for when you
are sitting with someone you know well and the conversation has stalled.

Live: <https://vacuumboots.github.io/katchup/>

309 questions, written by hand, tagged by era, topic, weight, kind, and hook. One card
on screen, three buttons: **Asked it**, **Skip**, **Never**. **Back** undoes the
last action. Follow-up prompts are one tap away if the answer starts a story.

No accounts, no backend, no analytics, no network calls after the page loads.

## Run it locally

```sh
python3 -m http.server 8099
```

Then open <http://127.0.0.1:8099/>. A plain `file://` load also works in most
browsers, but the local server is closer to what a host will serve.

## Deploy

The whole app is static: `index.html`, `app.js`, `styles.css`, `questions.json`,
`manifest.webmanifest`, and `icons/`. Any static host will do. Serve over HTTPS
if you want "Add to Home Screen" to give you a proper shortcut.

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

Then run the validator:

```sh
python3 scripts/validate_questions.py
```

It checks ids, enum values, follow-up counts, question marks, yes/no openers,
duplicates, and near-duplicates, prints the distributions against the spec
targets, and exits non-zero on hard errors. Passing it proves the deck's shape,
not its quality: it also writes `review.html`, one page with every question, for
a read-through.

## What is stored, and where

Everything lives in `localStorage` under `katchup_state_v1`: which ids have been
asked or never asked again, the current card, this session's skips, your filter
selection, and a timestamped history of asks.

There is no sync and no server. **Stats -> Export history** downloads the state
as JSON; **Import history** loads it back into a cleared browser. That is the
only backup path.

## Keyboard

Arrow left skips, arrow right marks asked, `n` marks never, `Backspace` or `u`
undoes. Escape closes a sheet. Swiping the card does skip and asked, but the
buttons are always the primary path.

## Files

```
index.html              markup, one screen plus two sheets
app.js                  state, selection, undo, filters, export/import
styles.css              gruvbox light and dark, system font stack
questions.json          the deck
manifest.webmanifest    home screen shortcut (no service worker, so no offline)
icons/                  placeholder PNGs, 192 and 512
scripts/validate_questions.py   validator and review.html generator
```
