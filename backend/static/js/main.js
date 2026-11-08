// Bonker Banker — page startup.

// HTMX normally ignores 4xx/5xx responses, so "Account not found" would silently
// show nothing. Swap them in like any other reply so the friendly message appears.
htmx.config.responseHandling = [
  { code: "204", swap: false },
  { code: "[23]..", swap: true },
  { code: "[45]..", swap: true, error: false },
];

// ---------- Simple / Advisor view ----------
// Content for advisors carries .advisor-only (hidden in Simple), and is never removed from the page.
// The choice is remembered per browser; storage can be blocked, so every access is wrapped.
const BBMode = (function () {
  const KEY = "bb-mode";

  function current() {
    return document.body.classList.contains("mode-advisor") ? "advisor" : "simple";
  }

  function save(mode) {
    try { localStorage.setItem(KEY, mode); } catch (e) { /* private window: the choice lasts this page only */ }
  }

  // Charts drawn while hidden have zero width; redraw anything now visible.
  function resizeCharts() {
    if (!window.echarts) return;
    document.querySelectorAll("[data-chart-ready]").forEach((el) => {
      if (el.offsetParent !== null) echarts.getInstanceByDom(el)?.resize();
    });
  }

  // Advisor mode opens the expanders marked data-advisor-open (the detail an advisor wants straight away).
  function syncDetails(root) {
    const advisor = current() === "advisor";
    (root || document).querySelectorAll("details[data-advisor-open]").forEach((d) => {
      if (d.dataset.userToggled || d.open === advisor) return;
      d.dataset.bbSync = "1";            // so the toggle handler below knows this wasn't a click
      d.open = advisor;
    });
  }

  function syncButtons() {
    const mode = current();
    document.querySelectorAll(".mode-btn").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
  }

  function set(mode, remember = true) {
    document.body.classList.toggle("mode-advisor", mode === "advisor");
    document.body.classList.toggle("mode-simple", mode !== "advisor");
    if (remember) save(mode);
    syncButtons();
    syncDetails();
    requestAnimationFrame(resizeCharts);
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".mode-btn");
    if (btn) set(btn.dataset.mode);
  });
  // An expander the user opened or closed themselves keeps their choice.
  document.addEventListener("toggle", (e) => {
    const d = e.target;
    if (!(d.matches && d.matches("details"))) return;
    if (d.dataset.bbSync) delete d.dataset.bbSync;
    else d.dataset.userToggled = "1";
  }, true);

  return { current, set, syncDetails, syncButtons, resizeCharts };
})();

// ---------- Tabs (any .tabs block: buttons [data-tab] + panels [data-tab-panel]) ----------
function initTabs(root) {
  (root || document).querySelectorAll(".tabs").forEach((box) => {
    if (box.dataset.tabsReady) return;
    box.dataset.tabsReady = "1";
    const buttons = box.querySelectorAll(":scope > .tab-list [data-tab]");
    const panels = box.querySelectorAll(":scope > [data-tab-panel]");
    function show(name) {
      buttons.forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
      panels.forEach((p) => (p.hidden = p.dataset.tabPanel !== name));
      requestAnimationFrame(BBMode.resizeCharts);
    }
    buttons.forEach((b) => b.addEventListener("click", () => show(b.dataset.tab)));
  });
}

// Charts inside a closed <details> are drawn at zero width; resize them when it opens.
document.addEventListener("toggle", (e) => {
  if (e.target.open && e.target.querySelectorAll) requestAnimationFrame(BBMode.resizeCharts);
}, true);

document.addEventListener("DOMContentLoaded", () => {
  BBMode.syncButtons();
  BBMode.syncDetails();
  initTabs();
  initCharts();
});

// Anything HTMX swaps in (e.g. an updated runway card): draw charts, wire tabs, apply the view.
document.addEventListener("htmx:afterSwap", (e) => {
  initCharts(e.target);
  initTabs(e.target);
  BBMode.syncDetails(e.target);
});
