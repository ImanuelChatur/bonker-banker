// Bonker Banker — page startup.

// Draw charts on first load.
document.addEventListener("DOMContentLoaded", () => initCharts());

// Draw charts inside anything HTMX swaps in (e.g. an updated runway card).
document.addEventListener("htmx:afterSwap", (e) => initCharts(e.target));