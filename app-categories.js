/* katchup: would you rather, Categories. Pick a deck, two items go head to head,
   the winner stays on. Nothing is stored: the bracket lives in memory for the
   visit, so every entry reshuffles and starts at duel 1. */

"use strict";

(() => {
  const el = {
    picker: document.getElementById("categoryPicker"),
    deckList: document.getElementById("deckList"),
    deckJumps: document.getElementById("deckJumps"),
    playRandom: document.getElementById("playRandom"),
    error: document.getElementById("categoryError"),

    duelCard: document.getElementById("duelCard"),
    duelMeta: document.getElementById("duelMeta"),
    duelPrompt: document.getElementById("duelPrompt"),
    champBtn: document.getElementById("champBtn"),
    champText: document.getElementById("champText"),
    champBlurb: document.getElementById("champBlurb"),
    challBtn: document.getElementById("challBtn"),
    challText: document.getElementById("challText"),
    challBlurb: document.getElementById("challBlurb"),
    duelFooter: document.getElementById("duelFooter"),
    undo: document.getElementById("duelUndoBtn"),
    restart: document.getElementById("duelRestartBtn"),

    championCard: document.getElementById("championCard"),
    championName: document.getElementById("championName"),
    championMeta: document.getElementById("championMeta"),
    trailList: document.getElementById("trailList"),
    championAgain: document.getElementById("championAgain"),
    championAnother: document.getElementById("championAnother"),
  };

  let decks = [];
  let deckById = new Map();
  let loaded = false;
  let wired = false;

  let deck = null;      // the deck being played
  let order = [];       // shuffled item ids, order[0] starts as champion
  let nextIndex = 0;    // index of the next challenger
  let champion = null;  // item object still standing
  let trail = [];       // items beaten, in order
  let history = [];     // one entry per duel, for undo

  /* ---------- content ---------- */

  async function ensureDecks() {
    if (loaded) return decks;
    decks = await Katchup.fetchJSON("categories", "categories.json");
    if (!Array.isArray(decks) || decks.length === 0) throw new Error("no decks");
    deckById = new Map(decks.map((entry) => [entry.id, entry]));
    loaded = true;
    return decks;
  }

  function itemById(id) {
    return deck ? deck.items.find((item) => item.id === id) : undefined;
  }

  function shuffle(list) {
    for (let i = list.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [list[i], list[j]] = [list[j], list[i]];
    }
    return list;
  }

  /* ---------- picker ---------- */

  function slug(text) {
    return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }

  function renderPicker() {
    el.deckList.innerHTML = "";
    el.deckJumps.innerHTML = "";

    const groups = [];
    for (const entry of decks) {
      const name = entry.group || "More";
      let bucket = groups.find((g) => g.name === name);
      if (!bucket) {
        bucket = { name, decks: [] };
        groups.push(bucket);
      }
      bucket.decks.push(entry);
    }

    for (const bucket of groups) {
      const block = document.createElement("section");
      block.className = "deck-group";
      block.id = `group-${slug(bucket.name)}`;

      const title = document.createElement("h2");
      title.className = "deck-group-title";
      title.textContent = bucket.name;
      block.appendChild(title);

      const list = document.createElement("ul");
      list.className = "deck-rows";

      for (const entry of bucket.decks) {
        const row = document.createElement("a");
        row.className = "deck-row";
        row.href = `#categories/${entry.id}`;

        const name = document.createElement("span");
        name.className = "deck-name";
        name.textContent = entry.name;

        const meta = document.createElement("span");
        meta.className = "deck-prompt";
        meta.textContent = `${entry.items.length} items · ${entry.prompt}`;

        row.appendChild(name);
        row.appendChild(meta);

        const holder = document.createElement("li");
        holder.appendChild(row);
        list.appendChild(holder);
      }

      block.appendChild(list);
      el.deckList.appendChild(block);

      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "deck-jump";
      chip.textContent = bucket.name;
      chip.setAttribute("aria-label", `Jump to ${bucket.name}`);
      chip.addEventListener("click", () => {
        block.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      el.deckJumps.appendChild(chip);
    }
  }

  /* ---------- bracket ---------- */

  function start(id) {
    const entry = deckById.get(id);
    if (!entry) {
      window.location.hash = "#categories";
      return;
    }

    deck = entry;
    order = shuffle(entry.items.map((item) => item.id));
    nextIndex = 1; // order[0] wears the belt first
    champion = itemById(order[0]);
    trail = [];
    history = [];

    el.error.hidden = true;
    Katchup.show("duel");
    renderDuel();
  }

  function setSide(text, blurb, item) {
    text.textContent = item.label;
    if (item.blurb) {
      blurb.textContent = item.blurb;
      blurb.hidden = false;
    } else {
      blurb.textContent = "";
      blurb.hidden = true;
    }
  }

  function renderDuel() {
    if (!deck || !champion || nextIndex >= order.length) return;

    const challenger = itemById(order[nextIndex]);
    if (!challenger) return;

    el.duelCard.hidden = false;
    el.duelFooter.hidden = false;
    el.duelMeta.textContent = `${deck.name} · duel ${nextIndex} of ${order.length - 1}`;
    el.duelPrompt.textContent = deck.prompt;

    setSide(el.champText, el.champBlurb, champion);
    setSide(el.challText, el.challBlurb, challenger);

    el.undo.disabled = history.length === 0;
  }

  function pick(side) {
    if (!deck || !champion || nextIndex >= order.length) return;

    const challenger = itemById(order[nextIndex]);
    if (!challenger) return;

    history.push({ champion, challengerId: challenger.id });

    if (side === "challenger") {
      trail.push(champion);
      champion = challenger;
    } else {
      trail.push(challenger);
    }

    nextIndex += 1;
    Katchup.fadeTo(el.duelCard, () => {
      if (nextIndex >= order.length) finish();
      else renderDuel();
    });
  }

  function undo() {
    const last = history.pop();
    if (!last) return;
    champion = last.champion;
    trail.pop();
    nextIndex -= 1;
    Katchup.fadeTo(el.duelCard, renderDuel);
  }

  function finish() {
    el.duelCard.hidden = true;
    el.duelFooter.hidden = true;
    renderChampion();
    Katchup.show("champion");
    const target = `#categories/${deck.id}/done`;
    if (window.location.hash !== target) window.location.hash = target;
  }

  function renderChampion() {
    if (!deck || !champion) return;
    el.championName.textContent = champion.label;
    el.championMeta.textContent = `${deck.name} · beat all ${order.length}`;
    el.trailList.innerHTML = "";

    trail.forEach((item, index) => {
      const row = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = item.label;
      const num = document.createElement("span");
      num.className = "trail-duel";
      num.textContent = `duel ${index + 1}`;
      row.appendChild(label);
      row.appendChild(num);
      el.trailList.appendChild(row);
    });
  }

  /* ---------- entry points from the router ---------- */

  async function enter() {
    wire();
    try {
      await ensureDecks();
    } catch (err) {
      el.picker.hidden = true;
      el.error.hidden = false;
      return;
    }
    el.error.hidden = true;
    el.picker.hidden = false;
    renderPicker();
  }

  async function duel(id) {
    wire();
    try {
      await ensureDecks();
    } catch (err) {
      el.picker.hidden = true;
      el.error.hidden = false;
      Katchup.show("categories");
      return;
    }

    if (deck && deck.id === id && champion && nextIndex < order.length) {
      Katchup.show("duel");
      renderDuel();
      return;
    }

    start(id);
  }

  async function done(id) {
    wire();
    try {
      await ensureDecks();
    } catch (err) {
      Katchup.show("categories");
      return;
    }

    if (deck && deck.id === id && champion && nextIndex >= order.length) {
      Katchup.show("champion");
      renderChampion();
      return;
    }

    // straight to a champion URL with no run in memory: start the deck over
    window.location.hash = `#categories/${id}`;
  }

  async function remainingText() {
    try {
      await ensureDecks();
    } catch (err) {
      return "";
    }
    return `${decks.length} categor${decks.length === 1 ? "y" : "ies"}`;
  }

  /* ---------- wiring ---------- */

  function wire() {
    if (wired) return;
    wired = true;

    el.champBtn.addEventListener("click", () => pick("champion"));
    el.challBtn.addEventListener("click", () => pick("challenger"));
    el.undo.addEventListener("click", undo);

    el.restart.addEventListener("click", () => {
      if (deck) start(deck.id);
    });

    el.playRandom.addEventListener("click", () => {
      if (!decks.length) return;
      const pickDeck = decks[Math.floor(Math.random() * decks.length)];
      window.location.hash = `#categories/${pickDeck.id}`;
    });

    el.championAgain.addEventListener("click", () => {
      if (!deck) return;
      const id = deck.id;
      start(id);
      window.location.hash = `#categories/${id}`;
    });

    el.championAnother.addEventListener("click", () => {
      window.location.hash = "#categories";
    });
  }

  Katchup.registerMode("categories", { enter, duel, done });
  Katchup.registerCount("categories", () => remainingText());
})();
