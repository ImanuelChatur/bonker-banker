// Upload page: pick or drop several PDFs (they accumulate, each can be removed), plus
// search / "flagged only" filtering of the transactions table (which arrives later via HTMX,
// so those listeners are delegated).
(() => {
  const drop = document.getElementById("drop");
  const input = document.getElementById("file");
  const list = document.getElementById("drop-files");
  const submit = document.getElementById("submit-btn");
  const clear = document.getElementById("clear-btn");
  if (!drop || !input) return;

  const MAX = window.BB_MAX_FILES || 10;
  let files = [];

  const sizeLabel = (n) => (n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB");

  // The <input> is the source of truth that HTMX submits, so mirror our list back into it.
  function sync() {
    const dt = new DataTransfer();
    files.forEach((f) => dt.items.add(f));
    input.files = dt.files;
    render();
  }

  function render() {
    list.replaceChildren(...files.map((f, i) => {
      const li = document.createElement("li");
      const name = document.createElement("span");
      name.className = "picked-name";
      name.textContent = f.name;
      const size = document.createElement("span");
      size.className = "text-muted";
      size.textContent = sizeLabel(f.size);
      const rm = document.createElement("button");
      rm.type = "button";
      rm.className = "picked-remove";
      rm.setAttribute("aria-label", `Remove ${f.name}`);
      rm.textContent = "×";
      rm.addEventListener("click", () => { files.splice(i, 1); sync(); });
      li.append(name, size, rm);
      return li;
    }));
    const n = files.length;
    submit.textContent = n > 1 ? `Parse ${n} statements` : "Parse statement" + (n ? "" : "s");
    clear.hidden = n === 0;
  }

  function add(newFiles) {
    for (const f of newFiles) {
      if (files.length >= MAX) break;
      if (!files.some((x) => x.name === f.name && x.size === f.size && x.lastModified === f.lastModified)) files.push(f);
    }
    sync();
  }

  input.addEventListener("change", () => add([...input.files]));
  clear.addEventListener("click", () => { files = []; sync(); });

  ["dragenter", "dragover"].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("is-over"); }));
  ["dragleave", "drop"].forEach((ev) =>
    drop.addEventListener(ev, (e) => {
      e.preventDefault();
      drop.classList.remove("is-over");
      if (ev === "drop") add([...e.dataTransfer.files]);
    }));

  function applyFilter() {
    const q = (document.getElementById("tx-search")?.value || "").trim().toLowerCase();
    const flaggedOnly = document.getElementById("tx-flagged")?.checked;
    let shown = 0;
    document.querySelectorAll("#tx-table tbody tr").forEach((tr) => {
      const ok = (!q || tr.dataset.text.includes(q)) && (!flaggedOnly || tr.dataset.flagged === "1");
      tr.hidden = !ok;
      if (ok) shown++;
    });
    const count = document.getElementById("tx-count");
    if (count) count.textContent = `${shown} shown`;
  }
  document.addEventListener("input", (e) => { if (e.target.id === "tx-search") applyFilter(); });
  document.addEventListener("change", (e) => { if (e.target.id === "tx-flagged") applyFilter(); });
})();
