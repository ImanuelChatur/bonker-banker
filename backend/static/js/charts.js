// Bonker Banker — chart helpers (Apache ECharts).
// Any element like <div class="chart" data-chart='{...}'> is drawn automatically.

const BB_COLORS = {
  brand: "#f97316",
  good: "#059669",
  bad: "#dc2626",
  muted: "#94a3b8",
};

// Line chart: labels on the x-axis, one or more named series.
// series = [{ name: "Buffer", data: [...] }, ...]
function renderLineChart(el, { labels, series, yName = "" }) {
  const chart = echarts.init(el);
  const palette = [BB_COLORS.brand, BB_COLORS.good, BB_COLORS.bad, BB_COLORS.muted];

  chart.setOption({
    color: palette,
    tooltip: { trigger: "axis" },
    legend: series.length > 1 ? { top: 0 } : undefined,
    grid: { left: 60, right: 20, top: series.length > 1 ? 40 : 20, bottom: 30 },
    xAxis: { type: "category", data: labels },
    yAxis: { type: "value", name: yName },
    series: series.map((s) => ({ type: "line", smooth: true, name: s.name, data: s.data })),
  });

  window.addEventListener("resize", () => chart.resize());
  return chart;
}

// Draw every chart on the page that has a data-chart attribute.
function initCharts(root = document) {
  root.querySelectorAll("[data-chart]").forEach((el) => {
    if (el.dataset.chartReady) return; // don't draw twice
    renderLineChart(el, JSON.parse(el.dataset.chart));
    el.dataset.chartReady = "1";
  });
}