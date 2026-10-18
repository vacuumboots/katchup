/* katchup core: screens, hash routing, sheets, and the helpers every mode shares.
   Mode logic lives in app-open.js (and later app-random.js, app-categories.js).
   Classic scripts, no modules, so file:// still works for local poking. */

"use strict";

const Katchup = (() => {
  const $ = (id) => document.getElementById(id);
  const $$ = (selector, root) => Array.from((root || document).querySelectorAll(selector));

  const routes = [];
  const modes = new Map();
  const counts = new Map();
  const sheetStack = new Set();
  const sheetCloseHooks = [];
  let activeScreen = null;
  let lastPath = null;

  /* ---------- storage ---------- */

  function readStore(key) {
    try {
      return JSON.parse(window.localStorage.getItem(key));
    } catch (err) {
      return null;
    }
  }

  function writeStore(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (err) {
      // storage full or blocked: the session still works, it just will not persist
      return false;
    }
  }

  /* ---------- content ---------- */

  const jsonCache = new Map();

  function fetchJSON(key, url) {
    if (!jsonCache.has(key)) {
      const promise = fetch(url, { cache: "default" })
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.json();
        })
        .catch((err) => {
          jsonCache.delete(key); // let the next attempt retry
          throw err;
        });
      jsonCache.set(key, promise);
    }
    return jsonCache.get(key);
  }

  /* ---------- motion ---------- */

  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function fadeTo(node, nextStep, ms = 120) {
    if (!node || reducedMotion()) {
      nextStep();
      return;
    }
    node.classList.add("is-fading");
    window.setTimeout(() => {
      nextStep();
      node.classList.remove("is-fading");
    }, ms);
  }

  /* ---------- sheets ---------- */

  function openSheet(sheet) {
    if (!sheet) return;
    $("scrim").hidden = false;
    sheet.hidden = false;
    sheetStack.add(sheet);
    sheet.tabIndex = -1;
    sheet.focus({ preventScroll: true });
  }

  function closeSheets() {
    const wasOpen = sheetStack.size > 0;
    $("scrim").hidden = true;
    for (const sheet of sheetStack) sheet.hidden = true;
    sheetStack.clear();
    if (wasOpen) for (const hook of sheetCloseHooks) hook();
  }

  function sheetOpen() {
    return sheetStack.size > 0;
  }

  function onSheetsClosed(hook) {
    sheetCloseHooks.push(hook);
  }

  /* ---------- chips ---------- */

  function makeChip(label, pressed, onClick) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = label;
    chip.setAttribute("aria-pressed", pressed ? "true" : "false");
    chip.addEventListener("click", onClick);
    return chip;
  }

  /* ---------- screens ---------- */

  function registerMode(name, handlers) {
    modes.set(name, handlers || {});
  }

  function registerCount(name, fn) {
    counts.set(name, fn);
  }

  function currentPath() {
    return window.location.hash.replace(/^#\/?/, "");
  }

  function show(name) {
    for (const screen of $$(".screen")) {
      screen.hidden = screen.dataset.screen !== name;
    }
    $("modesBtn").hidden = name === "home";
    for (const group of $$(".bar-group")) {
      group.hidden = group.dataset.for !== name;
    }
    activeScreen = name;
    if (name === "home") paintHome();

    // A screen swap hides the element the user just activated, which would strand
    // keyboard and screen-reader users on a hidden node. Move focus onto the screen
    // itself (tabindex="-1", labelled in the markup); the card's aria-live region
    // still announces whatever content renders.
    const screen = document.querySelector(`.screen[data-screen="${name}"]`);
    if (screen && document.activeElement !== screen) {
      screen.focus({ preventScroll: true });
    }
  }

  function isScreen(name) {
    return activeScreen === name;
  }

  async function paintHome() {
    for (const [name, fn] of counts) {
      const node = document.querySelector(`[data-count="${name}"]`);
      if (!node) continue;
      try {
        node.textContent = await fn();
      } catch (err) {
        node.textContent = "";
      }
    }
  }

  async function enterMode(name) {
    show(name);
    const handlers = modes.get(name);
    if (handlers && typeof handlers.enter === "function") await handlers.enter();
  }

  function runMode(name, hook, ...args) {
    const handlers = modes.get(name);
    if (handlers && typeof handlers[hook] === "function") handlers[hook](...args);
    else show("home");
  }

  function route(pattern, handler) {
    routes.push([pattern, handler]);
  }

  function render() {
    const path = currentPath();
    if (path === lastPath) return;
    lastPath = path;
    for (const [pattern, handler] of routes) {
      const match = path.match(pattern);
      if (match) {
        handler(match);
        return;
      }
    }
    // unknown hash: drop it and land on home
    window.location.replace(window.location.pathname + window.location.search);
  }

  function start() {
    route(/^$/, () => show("home"));
    route(/^open$/, () => enterMode("open"));
    route(/^random$/, () => enterMode("random"));
    route(/^categories\/([\w-]+)\/done$/, (match) => runMode("categories", "done", match[1]));
    route(/^categories\/([\w-]+)$/, (match) => runMode("categories", "duel", match[1]));
    route(/^categories$/, () => enterMode("categories"));

    $("modesBtn").addEventListener("click", () => {
      window.location.hash = "#";
    });

    $("scrim").addEventListener("click", closeSheets);

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && sheetOpen()) {
        event.preventDefault();
        closeSheets();
      }
    });

    window.addEventListener("hashchange", render);
    render();
  }

  window.addEventListener("DOMContentLoaded", start);

  return {
    $,
    $$,
    readStore,
    writeStore,
    fetchJSON,
    reducedMotion,
    fadeTo,
    openSheet,
    closeSheets,
    sheetOpen,
    onSheetsClosed,
    makeChip,
    registerMode,
    registerCount,
    currentPath,
    isScreen,
    show,
  };
})();
