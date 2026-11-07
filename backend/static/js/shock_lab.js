// Bonker Banker — Shock Lab controls.
// HTMX does the server calls (see hx-trigger on #shock-form); this file only
// keeps the slider labels, job-loss toggle, presets and twist-card sync in step.
(function () {
  const form = document.getElementById("shock-form");
  if (!form) return;

  const DEFAULTS = JSON.parse(document.getElementById("shock-defaults").textContent);
  const FIELDS = ["income_pct", "duration_months", "bills_pct", "one_off_months", "one_off_cost", "extra_spending"];
  const JOB_FIELDS = ["income_pct", "duration_months"];

  const FORMAT = {
    pct: (v) => `${v}%`,
    pct_up: (v) => (Number(v) === 0 ? "None" : `+${v}%`),
    months: (v) => (Number(v) === 0 ? "Ongoing" : `${v} months`),
    spend: (v) => (Number(v) === 0 ? "None" : `${v}× spending`),
  };

  // Show each slider's current value next to its label.
  function updateLabels() {
    form.querySelectorAll("output[data-for]").forEach((out) => {
      const input = form.elements[out.dataset.for];
      out.textContent = (FORMAT[out.dataset.fmt] || String)(input.value);
    });
  }

  // Job loss off → EI sliders disabled. Disabled inputs aren't sent, so the
  // server treats income as 100% and the duration as unset.
  function syncJobLoss() {
    const on = form.elements.job_loss.checked;
    JOB_FIELDS.forEach((n) => (form.elements[n].disabled = !on));
    form.querySelector('[data-group="job"]').classList.toggle("is-off", !on);
  }

  // Put a full set of values into the form (presets, reset, twist card).
  function applySettings(settings) {
    const s = { ...DEFAULTS, ...(settings || {}) };
    if (!("job_loss" in (settings || {})) && settings && "income_pct" in settings) {
      s.job_loss = Number(settings.income_pct) < 100; // twist card sends income_pct only
    }
    form.elements.job_loss.checked = !!s.job_loss;
    if (s.job_loss && Number(s.income_pct) >= 100) s.income_pct = DEFAULTS.income_pct;
    FIELDS.forEach((n) => {
      if (form.elements[n] && s[n] !== undefined && s[n] !== null) form.elements[n].value = s[n];
    });
    syncJobLoss();
    updateLabels();
  }

  function setActivePreset(btn) {
    document.querySelectorAll(".preset-btn").forEach((b) => b.classList.toggle("active", b === btn));
  }

  const run = () => htmx.trigger(form, "bbrun");

  // Typing or dragging: keep labels live (HTMX sends the request itself).
  form.addEventListener("input", (e) => {
    syncJobLoss();
    updateLabels();
    if (e.target.name !== "account_id") setActivePreset(null);
  });

  document.querySelectorAll(".preset-btn").forEach((btn) =>
    btn.addEventListener("click", () => {
      applySettings(JSON.parse(btn.dataset.preset));
      setActivePreset(btn);
      run();
    })
  );

  document.getElementById("reset-btn").addEventListener("click", () => {
    applySettings({});
    setActivePreset(null);
    run();
  });

  // After a twist card is interpreted, the server sends the parsed settings in an
  // HX-Trigger header. Move the sliders to match — without re-running the shock.
  document.body.addEventListener("twistParsed", (e) => {
    const d = e.detail && e.detail.value !== undefined ? e.detail.value : e.detail;
    applySettings(d);
    setActivePreset(null);
  });

  syncJobLoss();
  updateLabels();
})();
