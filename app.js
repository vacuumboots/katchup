/* katchup: one good question at a time.
   Static, no dependencies, no network calls after questions.json loads. */

"use strict";

const STORE_KEY = "katchup_state_v1";
const STATE_VERSION = 1;
const SKIP_WINDOW = 10; // cards shown before a skipped one may return

const VALUES = {
  weight: ["light", "medium", "heavy"],
  era: ["childhood", "teens", "young-adult", "career", "family", "now"],
  topic: [
    "music", "food", "cars", "work", "school", "places", "home",
    "firsts", "people", "money", "hobbies", "media", "advice",
  ],
  kind: ["memory", "opinion", "hypothetical"],
};

const GROUP_TITLES = { weight: "Weight", era: "Era", topic: "Topic", kind: "Kind" };

let questions = [];
let byId = new Map();
let state = null;
let lastAction = null; // one level of undo, session only
let pendingReset = false;
let resetTimer = null;

const el = {
  card: document.getElementById("card"),
  question: document.getElementById("question"),
  tags: document.getElementById("tags"),
  followupsToggle: document.getElementById("followupsToggle"),
  followups: document.getElementById("followups"),
  empty: document.getElementById("empty"),
  error: document.getElementById("error"),
  undoBtn: document.getElementById("undoBtn"),
  filtersBtn: document.getElementById("filtersBtn"),
  statsBtn: document.getElementById("statsBtn"),
  askedBtn: document.getElementById("askedBtn"),
  skipBtn: document.getElementById("skipBtn"),
  neverBtn: document.getElementById("neverBtn"),
  emptyFilters: document.getElementById("emptyFilters"),
  emptyReset: document.getElementById("emptyReset"),
  scrim: document.getElementById("scrim"),
  filtersSheet: document.getElementById("filtersSheet"),
  statsSheet: document.getElementById("statsSheet"),
  filterCount: document.getElementById("filterCount"),
  filterGroups: document.getElementById("filterGroups"),
  filtersDone: document.getElementById("filtersDone"),
  statsDone: document.getElementById("statsDone"),
  statAsked: document.getElementById("statAsked"),
  statRemaining: document.getElementById("statRemaining"),
  exportBtn: document.getElementById("exportBtn"),
  importBtn: document.getElementById("importBtn"),
  importFile: document.getElementById("importFile"),
  resetBtn: document.getElementById("resetBtn"),
  resetHint: document.getElementById("resetHint"),
};

/* ---------- state ---------- */

function defaultState() {
  return {
    version: STATE_VERSION,
    asked: [],
    never: [],
    skippedThisSession: [],
    filters: { weight: ["light", "medium"], era: [], topic: [], kind: [] },
    currentId: null,
    history: [],
    shownCards: 0,
  };
}

function migrate(raw) {
  const base = defaultState();
  if (!raw || typeof raw !== "object") return base;

  const next = { ...base, ...raw, version: STATE_VERSION };
  next.asked = Array.isArray(raw.asked) ? raw.asked.filter((id) => typeof id === "string") : [];
  next.never = Array.isArray(raw.never) ? raw.never.filter((id) => typeof id === "string") : [];
  next.history = Array.isArray(raw.history)
    ? raw.history.filter((h) => h && typeof h.id === "string")
    : [];
  next.skippedThisSession = Array.isArray(raw.skippedThisSession)
    ? raw.skippedThisSession
        .map((entry) =>
          typeof entry === "string" ? { id: entry, at: 0 } : entry
        )
        .filter((entry) => entry && typeof entry.id === "string")
    : [];
  next.shownCards = Number.isFinite(raw.shownCards) ? raw.shownCards : 0;
  next.currentId = typeof raw.currentId === "string" ? raw.currentId : null;

  next.filters = { ...base.filters };
  if (raw.filters && typeof raw.filters === "object") {
    for (const group of Object.keys(VALUES)) {
      const value = raw.filters[group];
      next.filters[group] = Array.isArray(value)
        ? value.filter((v) => VALUES[group].includes(v))
        : [];
    }
  }
  return next;
}

function loadState() {
  try {
    return migrate(JSON.parse(localStorage.getItem(STORE_KEY)));
  } catch (err) {
    return defaultState();
  }
}

function saveState() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state));
  } catch (err) {
    /* storage full or blocked: the session still works, it just will not persist */
  }
}

/* ---------- selection ---------- */

function inGroup(value, selected) {
  return selected.length === 0 || selected.includes(value);
}

function matchesFilters(q) {
  const f = state.filters;
  return (
    inGroup(q.weight, f.weight) &&
    inGroup(q.era, f.era) &&
    inGroup(q.topic, f.topic) &&
    inGroup(q.kind, f.kind)
  );
}

function isAvailable(id) {
  return !state.asked.includes(id) && !state.never.includes(id);
}

function pool() {
  return questions.filter((q) => isAvailable(q.id) && matchesFilters(q));
}

function skipEntry(id) {
  return state.skippedThisSession.find((entry) => entry.id === id);
}

function pickNext(excludeId) {
  const all = pool().filter((q) => q.id !== excludeId);
  if (all.length === 0) return null;

  const fresh = [];
  const returning = [];
  const recent = [];

  for (const q of all) {
    const entry = skipEntry(q.id);
    if (!entry) fresh.push(q);
    else if (state.shownCards - entry.at >= SKIP_WINDOW) returning.push(q);
    else recent.push(q);
  }

  const list = fresh.length ? fresh : returning.length ? returning : recent;
  return list[Math.floor(Math.random() * list.length)];
}

/* ---------- rendering ---------- */

function showCard(q) {
  el.error.hidden = true;
  el.empty.hidden = true;
  el.card.hidden = false;
  el.question.textContent = q.text;
  el.tags.textContent = `${q.era} · ${q.topic}`;

  el.followups.innerHTML = "";
  for (const followup of q.followups || []) {
    const li = document.createElement("li");
    li.textContent = followup;
    el.followups.appendChild(li);
  }
  el.followups.hidden = true;
  el.followupsToggle.hidden = !(q.followups && q.followups.length);
  el.followupsToggle.setAttribute("aria-expanded", "false");
  el.followupsToggle.textContent = "Follow-ups";

  setActionsEnabled(true);
  el.undoBtn.disabled = !lastAction;
}

function showEmpty() {
  el.card.hidden = true;
  el.error.hidden = true;
  el.empty.hidden = false;
  setActionsEnabled(false);
  el.undoBtn.disabled = !lastAction;
}

function showError() {
  el.card.hidden = true;
  el.empty.hidden = true;
  el.error.hidden = false;
  setActionsEnabled(false);
  el.undoBtn.disabled = true;
}

function setActionsEnabled(enabled) {
  el.askedBtn.disabled = !enabled;
  el.skipBtn.disabled = !enabled;
  el.neverBtn.disabled = !enabled;
}

function fadeTo(nextStep) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) {
    nextStep();
    return;
  }
  el.card.classList.add("is-fading");
  window.setTimeout(() => {
    nextStep();
    el.card.classList.remove("is-fading");
  }, 120);
}

function advance() {
  const next = pickNext(state.currentId);
  if (!next) {
    state.currentId = null;
    saveState();
    showEmpty();
    return;
  }
  state.shownCards += 1;
  state.currentId = next.id;
  saveState();
  fadeTo(() => showCard(next));
}

/* ---------- actions ---------- */

function act(kind) {
  const current = byId.get(state.currentId);
  if (!current) return;
  const id = current.id;

  if (kind === "asked") {
    if (!state.asked.includes(id)) state.asked.push(id);
    state.history.push({ id, askedAt: new Date().toISOString() });
    state.skippedThisSession = state.skippedThisSession.filter((e) => e.id !== id);
  } else if (kind === "never") {
    if (!state.never.includes(id)) state.never.push(id);
    state.skippedThisSession = state.skippedThisSession.filter((e) => e.id !== id);
  } else if (kind === "skip") {
    state.skippedThisSession = state.skippedThisSession.filter((e) => e.id !== id);
    state.skippedThisSession.push({ id, at: state.shownCards });
  }

  lastAction = { kind, id };
  advance();
}

function undo() {
  if (!lastAction) return;
  const { kind, id } = lastAction;

  if (kind === "asked") {
    state.asked = state.asked.filter((x) => x !== id);
    for (let i = state.history.length - 1; i >= 0; i -= 1) {
      if (state.history[i].id === id) {
        state.history.splice(i, 1);
        break;
      }
    }
  } else if (kind === "never") {
    state.never = state.never.filter((x) => x !== id);
  } else if (kind === "skip") {
    state.skippedThisSession = state.skippedThisSession.filter((e) => e.id !== id);
  }

  lastAction = null;
  state.currentId = id;
  state.shownCards = Math.max(0, state.shownCards - 1);
  saveState();

  const q = byId.get(id);
  if (q && isAvailable(id) && matchesFilters(q)) {
    fadeTo(() => showCard(q));
  } else {
    advance();
  }
}

/* ---------- sheets ---------- */

function openSheet(sheet) {
  el.scrim.hidden = false;
  sheet.hidden = false;
  if (sheet === el.filtersSheet) renderFilters();
  if (sheet === el.statsSheet) renderStats();
  sheet.tabIndex = -1;
  sheet.focus({ preventScroll: true });
}

function closeSheets() {
  el.scrim.hidden = true;
  el.filtersSheet.hidden = true;
  el.statsSheet.hidden = true;
  pendingReset = false;
  el.resetHint.hidden = true;
  if (resetTimer) window.clearTimeout(resetTimer);
}

function renderFilters() {
  el.filterGroups.innerHTML = "";
  for (const group of Object.keys(VALUES)) {
    const wrapper = document.createElement("div");
    wrapper.className = "group";

    const heading = document.createElement("h3");
    heading.textContent = GROUP_TITLES[group];
    wrapper.appendChild(heading);

    const chips = document.createElement("div");
    chips.className = "chips";

    const allChip = makeChip("All", state.filters[group].length === 0, () => {
      state.filters[group] = [];
      applyFilters();
    });
    chips.appendChild(allChip);

    for (const value of VALUES[group]) {
      const pressed = state.filters[group].includes(value);
      chips.appendChild(
        makeChip(value, pressed, () => {
          const current = state.filters[group];
          if (current.length === 0) {
            // everything was selected: tapping one narrows to just that one
            state.filters[group] = [value];
          } else if (current.includes(value)) {
            state.filters[group] = current.filter((v) => v !== value);
          } else {
            state.filters[group] = [...current, value];
          }
          if (state.filters[group].length === VALUES[group].length) state.filters[group] = [];
          applyFilters();
        })
      );
    }

    wrapper.appendChild(chips);
    el.filterGroups.appendChild(wrapper);
  }
  updateFilterCount();
}

function makeChip(label, pressed, onClick) {
  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = "chip";
  chip.textContent = label;
  chip.setAttribute("aria-pressed", pressed ? "true" : "false");
  chip.addEventListener("click", onClick);
  return chip;
}

function updateFilterCount() {
  const count = pool().length;
  el.filterCount.textContent = `${count} question${count === 1 ? "" : "s"} left in this filter`;
}

function applyFilters() {
  saveState();
  renderFilters();
  const current = byId.get(state.currentId);
  if (current && isAvailable(current.id) && matchesFilters(current)) return;
  advance();
}

function renderStats() {
  el.statAsked.textContent = String(state.asked.length);
  el.statRemaining.textContent = String(
    questions.filter((q) => isAvailable(q.id)).length
  );
  pendingReset = false;
  el.resetHint.hidden = true;
}

/* ---------- export / import ---------- */

function exportHistory() {
  const payload = { app: "katchup", exportedAt: new Date().toISOString(), state };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const stamp = new Date().toISOString().slice(0, 10);
  link.href = url;
  link.download = `katchup-history-${stamp}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function importHistory(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result));
      const incoming = parsed && parsed.state ? parsed.state : parsed;
      if (!incoming || typeof incoming !== "object" || !Array.isArray(incoming.asked)) {
        throw new Error("not a katchup history file");
      }
      state = migrate(incoming);
      lastAction = null;
      saveState();
      closeSheets();
      const current = byId.get(state.currentId);
      if (current && isAvailable(current.id) && matchesFilters(current)) showCard(current);
      else advance();
    } catch (err) {
      el.resetHint.textContent = "That file could not be read as a katchup history export.";
      el.resetHint.hidden = false;
    }
  };
  reader.readAsText(file);
}

function resetHistory() {
  state.asked = [];
  state.never = [];
  state.history = [];
  state.skippedThisSession = [];
  state.currentId = null;
  state.shownCards = 0;
  lastAction = null;
  saveState();
  closeSheets();
  advance();
}

/* ---------- wiring ---------- */

function wire() {
  el.askedBtn.addEventListener("click", () => act("asked"));
  el.skipBtn.addEventListener("click", () => act("skip"));
  el.neverBtn.addEventListener("click", () => act("never"));
  el.undoBtn.addEventListener("click", undo);

  el.followupsToggle.addEventListener("click", () => {
    const open = el.followupsToggle.getAttribute("aria-expanded") === "true";
    el.followupsToggle.setAttribute("aria-expanded", open ? "false" : "true");
    el.followups.hidden = open;
    el.followupsToggle.textContent = open ? "Follow-ups" : "Hide follow-ups";
  });

  el.filtersBtn.addEventListener("click", () => openSheet(el.filtersSheet));
  el.statsBtn.addEventListener("click", () => openSheet(el.statsSheet));
  el.filtersDone.addEventListener("click", closeSheets);
  el.statsDone.addEventListener("click", closeSheets);
  el.scrim.addEventListener("click", closeSheets);
  el.emptyFilters.addEventListener("click", () => openSheet(el.filtersSheet));
  el.emptyReset.addEventListener("click", resetHistory);

  el.exportBtn.addEventListener("click", exportHistory);
  el.importBtn.addEventListener("click", () => el.importFile.click());
  el.importFile.addEventListener("change", () => {
    const file = el.importFile.files && el.importFile.files[0];
    if (file) importHistory(file);
    el.importFile.value = "";
  });

  el.resetBtn.addEventListener("click", () => {
    if (!pendingReset) {
      pendingReset = true;
      el.resetHint.hidden = false;
      resetTimer = window.setTimeout(() => {
        pendingReset = false;
        el.resetHint.hidden = true;
      }, 5000);
      return;
    }
    if (resetTimer) window.clearTimeout(resetTimer);
    resetHistory();
  });

  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (!el.filtersSheet.hidden || !el.statsSheet.hidden) {
      if (event.key === "Escape") closeSheets();
      return;
    }
    const tag = (event.target && event.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA") return;
    if (event.key === "ArrowLeft") act("skip");
    else if (event.key === "ArrowRight") act("asked");
    else if (event.key.toLowerCase() === "n") act("never");
    else if (event.key === "Backspace" || event.key.toLowerCase() === "u") {
      event.preventDefault();
      undo();
    }
  });

  // optional swipe: buttons stay the primary path
  let startX = 0;
  let startY = 0;
  let tracking = false;
  el.stage = document.querySelector(".stage");
  el.stage.addEventListener("pointerdown", (event) => {
    if (event.target.closest("button")) return;
    tracking = true;
    startX = event.clientX;
    startY = event.clientY;
  });
  el.stage.addEventListener("pointerup", (event) => {
    if (!tracking) return;
    tracking = false;
    const dx = event.clientX - startX;
    const dy = event.clientY - startY;
    if (Math.abs(dx) < 70 || Math.abs(dy) > 50) return;
    act(dx < 0 ? "skip" : "asked");
  });
  el.stage.addEventListener("pointercancel", () => {
    tracking = false;
  });
}

async function boot() {
  state = loadState();
  wire();
  try {
    const response = await fetch("questions.json", { cache: "default" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    questions = await response.json();
    if (!Array.isArray(questions) || questions.length === 0) throw new Error("no questions");
  } catch (err) {
    showError();
    return;
  }

  byId = new Map(questions.map((q) => [q.id, q]));

  // drop ids that no longer exist in the deck
  const known = (id) => byId.has(id);
  state.asked = state.asked.filter(known);
  state.never = state.never.filter(known);
  state.history = state.history.filter((h) => known(h.id));
  state.skippedThisSession = state.skippedThisSession.filter((entry) => known(entry.id));

  const current = byId.get(state.currentId);
  if (current && isAvailable(current.id) && matchesFilters(current)) {
    saveState();
    showCard(current);
  } else {
    advance();
  }
}

boot();
