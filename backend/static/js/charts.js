// Bonker Banker — chart helpers (Apache ECharts).
// Any element like <div class="chart" data-chart='{...}'> is drawn automatically.
// Colours come from the CSS theme tokens, so charts follow light/dark mode.

const BB_COLORS = {
  brand: "#f97316",
  good: "#059669",
  bad: "#dc2626",
  muted: "#94a3b8",
};

function themeColors() {
  const cs = getComputedStyle(document.documentElement);
  const v = (name, fallback) => cs.getPropertyValue(name).trim() || fallback;
  return { ink: v("--ink", "#0f172a"), muted: v("--muted", "#64748b"), border: v("--border", "#e2e8f0"),
           surface: v("--surface", "#ffffff") };
}

// 12500 -> "12.5k" so axis labels stay short.
function compactNumber(n) {
  const a = Math.abs(n);
  if (a >= 1e6) return +(n / 1e6).toFixed(1) + "M";
  if (a >= 1e3) return +(n / 1e3).toFixed(1) + "k";
  return String(n);
}

// Line chart: labels on the x-axis, one or more named series.
// series = [{ name: "Buffer", data: [...], color?: "#hex", smooth?: false }, ...]
function renderLineChart(el, { labels, series, yName = "" }) {
  const chart = echarts.init(el);
  const t = themeColors();
  // Colour carries meaning only: plain lines are neutral ink; series that mean "bad" pass their own colour.
  const palette = [t.ink, "#8b94a3", BB_COLORS.brand, BB_COLORS.good];
  const single = series.length === 1;

  chart.setOption({
    color: palette,
    textStyle: { color: t.muted, fontFamily: "inherit" },
    tooltip: {
      trigger: "axis",
      backgroundColor: t.surface,
      borderColor: t.border,
      textStyle: { color: t.ink },
      valueFormatter: (v) => (typeof v === "number" ? "$" + v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : v),
    },
    legend: single ? undefined : { top: 0, textStyle: { color: t.muted } },
    grid: { left: 56, right: 20, top: single ? 24 : 44, bottom: 30 },
    xAxis: {
      type: "category", data: labels, boundaryGap: false,
      axisLine: { lineStyle: { color: t.border } }, axisTick: { show: false }, axisLabel: { color: t.muted },
    },
    yAxis: {
      type: "value", name: yName, nameTextStyle: { color: t.muted, align: "left" },
      axisLabel: { color: t.muted, formatter: compactNumber },
      splitLine: { lineStyle: { color: t.border, type: "dashed" } },
    },
    series: series.map((s, i) => {
      const color = s.color || palette[i % palette.length];
      return {
        type: "line", name: s.name, data: s.data, smooth: s.smooth !== false,
        showSymbol: false, lineStyle: { width: 2.5, color }, itemStyle: { color },
      };
    }),
  });
  return chart;
}

// Donut chart: { kind: "donut", items: [{ name, value }], center?: "label" }
function renderDonutChart(el, { items, center = "" }) {
  const chart = echarts.init(el);
  const t = themeColors();
  const cs = getComputedStyle(document.documentElement);
  // One accent, then neutrals: neighbouring slices never share a hue.
  const palette = ["--c1", "--c2", "--c4", "--c6", "--c8", "--c3", "--c5"].map((v, i) =>
    cs.getPropertyValue(v).trim() || [BB_COLORS.brand, "#14181f", "#566070", "#8b94a3", "#bcc3ce", "#e0764a", "#eaa88a"][i]);
  chart.setOption({
    color: palette,
    textStyle: { fontFamily: "inherit" },
    tooltip: {
      trigger: "item", backgroundColor: t.surface, borderColor: t.border, textStyle: { color: t.ink },
      valueFormatter: (v) => "$" + Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 }) + "/mo",
    },
    legend: { bottom: 0, icon: "circle", textStyle: { color: t.muted } },
    title: center ? { text: center, left: "center", top: "38%", textStyle: { color: t.ink, fontSize: 15, fontWeight: 700 } } : undefined,
    series: [{
      type: "pie", radius: ["52%", "74%"], center: ["50%", "44%"], avoidLabelOverlap: true, minAngle: 4,
      itemStyle: { borderColor: t.surface, borderWidth: 3, borderRadius: 6 },
      label: { show: false }, data: items,
    }],
  });
  return chart;
}

// Heatmap: { kind: "heatmap", xLabels, yLabels, xName, yName, data: [[xIndex, yIndex, value], ...], unit: "%" }
function renderHeatmap(el, { xLabels, yLabels, xName = "", yName = "", data, unit = "%" }) {
  const chart = echarts.init(el);
  const t = themeColors();
  const cs = getComputedStyle(document.documentElement);
  const hot = cs.getPropertyValue("--bad").trim() || BB_COLORS.bad;   // more accounts out of savings = worse
  const cool = cs.getPropertyValue("--surface-2").trim() || "#f1f4f9";
  chart.setOption({
    textStyle: { fontFamily: "inherit", color: t.muted },
    tooltip: {
      backgroundColor: t.surface, borderColor: t.border, textStyle: { color: t.ink },
      formatter: (p) => `${xName} ${xLabels[p.value[0]]}, ${yName} ${yLabels[p.value[1]]}<br><b>${p.value[2]}${unit}</b> run out within 6 months`,
    },
    grid: { left: 70, right: 16, top: 10, bottom: 50 },
    xAxis: { type: "category", data: xLabels, name: xName, nameLocation: "middle", nameGap: 32,
             axisTick: { show: false }, axisLine: { show: false }, axisLabel: { color: t.muted } },
    yAxis: { type: "category", data: yLabels, name: yName, nameLocation: "middle", nameGap: 52,
             axisTick: { show: false }, axisLine: { show: false }, axisLabel: { color: t.muted } },
    visualMap: { min: 0, max: 100, show: false, inRange: { color: [cool, hot] } },
    series: [{
      type: "heatmap",
      // Dark cells get white labels so the number stays readable.
      data: data.map((d) => ({ value: d, label: { color: d[2] >= 55 ? "#fff" : t.ink } })),
      label: { show: true, formatter: (p) => p.value[2] + unit, color: t.ink, fontWeight: 700, fontSize: 15 },
      itemStyle: { borderColor: t.surface, borderWidth: 3, borderRadius: 6 },
      emphasis: { itemStyle: { borderColor: t.ink } },
    }],
  });
  return chart;
}

// Draw every chart on the page that has a data-chart attribute.
function initCharts(root = document) {
  root.querySelectorAll("[data-chart]").forEach((el) => {
    if (el.dataset.chartReady) return; // don't draw twice
    const cfg = JSON.parse(el.dataset.chart);
    ({ donut: renderDonutChart, heatmap: renderHeatmap }[cfg.kind] || renderLineChart)(el, cfg);
    el.dataset.chartReady = "1";
  });
}

// One shared resize handler instead of one per chart.
window.addEventListener("resize", () => {
  document.querySelectorAll("[data-chart-ready]").forEach((el) => echarts.getInstanceByDom(el)?.resize());
});

// Redraw when the system switches between light and dark so axis/tooltip colours stay readable.
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  document.querySelectorAll("[data-chart-ready]").forEach((el) => {
    echarts.getInstanceByDom(el)?.dispose();
    delete el.dataset.chartReady;
  });
  initCharts();
});
