// Bonker Banker — page startup.

// HTMX normally ignores 4xx/5xx responses, so "Account not found" would silently
// show nothing. Swap them in like any other reply so the friendly message appears.
htmx.config.responseHandling = [
  { code: "204", swap: false },
  { code: "[23]..", swap: true },
  { code: "[45]..", swap: true, error: false },
];

// Draw charts on first load.
document.addEventListener("DOMContentLoaded", () => initCharts());

// Draw charts inside anything HTMX swaps in (e.g. an updated runway card).
document.addEventListener("htmx:afterSwap", (e) => initCharts(e.target));
