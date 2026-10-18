/* katchup: would you rather, random. Two options, pick one, next.
   Nothing about a run is stored: every entry shuffles a fresh order. The only
   persisted thing is this mode's own filters, in katchup_random_v1. */

"use strict";

(() => {
  const STORE_KEY = "katchup_random_v1";
  const STORE_VERSION = 1;
  const WEIGHTS = ["light", "medium"];
  const ALL_WEIGHTS = ["light", "medium"];
  const TOPICS = [
    "music", "food", "cars", "work", "school", "places", "home",
    "firsts", "people", "money", "hobbies", "media", "advice",
  ];

  const el = {
    card: document.getElementById("randomCard"),
    topic: document.getElementById("randomTopic"),
    choiceA: document.getElementById("choiceA"),
    choiceAText: document.getElementById("choiceAText"),
    choiceB: document.getElementById("choiceB"),
    choiceBText: document.getElementById("choiceBText"),
    empty: document.getElementById("randomEmpty"),
    done: document.getElementById("randomDone"),
    error: document.getElementById("randomError"),
    footer: document.getElementById("randomFooter"),
    undo: document.getElementById("randomUndoBtn"),
    skip: document.getElementById("randomSkipBtn"),
    progress: document.getElementById("randomProgress"),
    filtersBtn: document.getElementById("randomFiltersBtn"),
    sheet: document.getElementById("randomFiltersSheet"),
    filterCount: document.getElementById("randomFilterCount"),
    filterGroups: document.getElementById("randomFilterGroups"),
    filtersDone: document.getElementById("randomFiltersDone"),
    emptyFilters: document.getElementById("randomEmptyFilters"),
    again: document.getElementById("randomAgain"),
  };

  let pairs = [];
  let pairById = new Map();
  let loaded = false;
  let wired = false;

  let filters = { topic: [], weight: ALL_WEIGHTS.slice() };
  let order = [];
  let at = 0;
  let picks = [];

  /* ---------- preferences ---------- */

  function defaultFilters() {
    return { topic: [], weight: ALL_WEIGHTS.slice() };
  }

  function readPrefs() {
    const raw = Katchup.readStore(STORE_KEY);
    const next = defaultFilters();
    if (!raw || typeof raw !== "object" || !raw.filters) return next;

    if (Array.isArray(raw.filters.topic)) {
      next.topic = raw.filters.topic.filter((t) => TOPICS.includes(t));
    }
    if (Array.isArray(raw.filters.weight)) {
      const kept = raw.filters.weight.filter((w) => WEIGHTS.includes(w));
      next.weight = kept.length ? kept : ALL_WEIGHTS.slice();
    }
    return next;
  }

  function savePrefs() {
    Katchup.writeStore(STORE_KEY, { version: STORE_VERSION, filters });
  }

  /* ---------- deck ---------- */

  async function ensureDeck() {
    if (loaded) return pairs;
    pairs = await Katchup.fetchJSON("wouldrather", "wouldrather.json");
    if (!Array.isArray(pairs) || pairs.length === 0) throw new Error("no pairs");
    pairById = new Map(pairs.map((pair) => [pair.id, pair]));
    loaded = true;
    return pairs;
  }

  function matches(pair) {
    const topicOk = filters.topic.length === 0 || filters.topic.includes(pair.topic);
    return topicOk && filters.weight.includes(pair.weight);
  }

  function poolCount() {
    return pairs.filter(matches).length;
  }

  function shuffle(list) {
    for (let i = list.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [list[i], list[j]] = [list[j], list[i]];
    }
    return list;
  }

  function buildOrder() {
    order = shuffle(pairs.filter(matches).map((pair) => pair.id));
    at = 0;
    picks = [];
  }

  /* ---------- rendering ---------- */

  function setChoice(button, textNode, text) {
    textNode.textContent = text;
    button.classList.remove("is-long");
    button.setAttribute("aria-label", text);
    // three lines at 20px overflow the 96px floor; drop to 17px instead of clipping
    if (button.scrollHeight > 100) button.classList.add("is-long");
  }

  function render() {
    if (order.length === 0) {
      showEmpty();
      return;
    }
    if (at >= order.length) {
      showDone();
      return;
    }

    const pair = pairById.get(order[at]);
    if (!pair) {
      buildOrder();
      render();
      return;
    }

    el.error.hidden = true;
    el.empty.hidden = true;
    el.done.hidden = true;
    el.card.hidden = false;
    el.footer.hidden = false;

    el.topic.textContent = pair.topic;
    setChoice(el.choiceA, el.choiceAText, pair.a);
    setChoice(el.choiceB, el.choiceBText, pair.b);

    el.undo.disabled = picks.length === 0;
    el.progress.textContent = `${at + 1} of ${order.length}`;
  }

  function showEmpty() {
    el.card.hidden = true;
    el.done.hidden = true;
    el.error.hidden = true;
    el.empty.hidden = false;
    el.footer.hidden = true;
  }

  function showDone() {
    el.card.hidden = true;
    el.empty.hidden = true;
    el.error.hidden = true;
    el.done.hidden = false;
    el.footer.hidden = true;
  }

  function showError() {
    el.card.hidden = true;
    el.empty.hidden = true;
    el.done.hidden = true;
    el.error.hidden = false;
    el.footer.hidden = true;
  }

  /* ---------- run ---------- */

  function pick(side) {
    if (order.length === 0 || at >= order.length) return;
    picks.push({ id: order[at], index: at, side });
    at += 1;
    Katchup.fadeTo(el.card, render);
  }

  function undo() {
    const last = picks.pop();
    if (!last) return;
    const index = order.indexOf(last.id);
    at = index >= 0 ? index : Math.max(0, Math.min(last.index, order.length - 1));
    Katchup.fadeTo(el.card, render);
  }

  function skip() {
    if (order.length === 0 || at >= order.length) return;
    const id = order[at];
    order.splice(at, 1);
    order.push(id); // back in the pool, later in this visit
    if (at >= order.length - 1) at = 0;
    Katchup.fadeTo(el.card, render);
  }

  /* ---------- filters sheet ---------- */

  function renderFilters() {
    el.filterGroups.innerHTML = "";

    const topicGroup = document.createElement("div");
    topicGroup.className = "group";
    const topicHeading = document.createElement("h3");
    topicHeading.textContent = "Topic";
    topicGroup.appendChild(topicHeading);
    const topicChips = document.createElement("div");
    topicChips.className = "chips";
    topicChips.appendChild(
      Katchup.makeChip("All", filters.topic.length === 0, () => {
        filters.topic = [];
        applyFilters();
      })
    );
    for (const topic of TOPICS) {
      const pressed = filters.topic.length === 0 || filters.topic.includes(topic);
      topicChips.appendChild(
        Katchup.makeChip(topic, pressed, () => {
          const current = filters.topic;
          if (current.length === 0) filters.topic = [topic];
          else if (current.includes(topic)) filters.topic = current.filter((t) => t !== topic);
          else filters.topic = [...current, topic];
          if (filters.topic.length === TOPICS.length) filters.topic = [];
          applyFilters();
        })
      );
    }
    topicGroup.appendChild(topicChips);
    el.filterGroups.appendChild(topicGroup);

    const weightGroup = document.createElement("div");
    weightGroup.className = "group";
    const weightHeading = document.createElement("h3");
    weightHeading.textContent = "Weight";
    weightGroup.appendChild(weightHeading);
    const weightChips = document.createElement("div");
    weightChips.className = "chips";
    for (const weight of WEIGHTS) {
      weightChips.appendChild(
        Katchup.makeChip(weight, filters.weight.includes(weight), () => {
          const current = filters.weight;
          if (current.includes(weight)) {
            // keep at least one weight on, so the pool is never empty by accident
            if (current.length === 1) filters.weight = ALL_WEIGHTS.slice();
            else filters.weight = current.filter((w) => w !== weight);
          } else {
            filters.weight = [...current, weight];
          }
          if (filters.weight.length === WEIGHTS.length) filters.weight = ALL_WEIGHTS.slice();
          applyFilters();
        })
      );
    }
    weightGroup.appendChild(weightChips);
    el.filterGroups.appendChild(weightGroup);

    el.filterCount.textContent = `${poolCount()} pairs in this filter`;
  }

  function applyFilters() {
    savePrefs();
    buildOrder();
    renderFilters();
    render();
  }

  /* ---------- wiring ---------- */

  function wire() {
    if (wired) return;
    wired = true;

    el.choiceA.addEventListener("click", () => pick("a"));
    el.choiceB.addEventListener("click", () => pick("b"));
    el.undo.addEventListener("click", undo);
    el.skip.addEventListener("click", skip);

    el.filtersBtn.addEventListener("click", () => {
      Katchup.openSheet(el.sheet);
      renderFilters();
    });
    el.emptyFilters.addEventListener("click", () => {
      Katchup.openSheet(el.sheet);
      renderFilters();
    });
    el.filtersDone.addEventListener("click", Katchup.closeSheets);
    el.again.addEventListener("click", () => {
      buildOrder();
      render();
    });
  }

  /* ---------- entry point ---------- */

  async function enter() {
    wire();
    filters = readPrefs();
    try {
      await ensureDeck();
    } catch (err) {
      showError();
      return;
    }
    buildOrder();
    render();
  }

  async function remainingText() {
    filters = readPrefs();
    try {
      await ensureDeck();
    } catch (err) {
      return "";
    }
    return `${poolCount()} pair${poolCount() === 1 ? "" : "s"}`;
  }

  Katchup.registerMode("random", { enter });
  Katchup.registerCount("random", () => remainingText());
})();
