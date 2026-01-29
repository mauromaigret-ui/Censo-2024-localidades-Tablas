const statusEl = document.getElementById("status");
const layerSelect = document.getElementById("layerSelect");
const loadVarsBtn = document.getElementById("loadVarsBtn");
const filterInput = document.getElementById("filterInput");
const filterMeta = document.getElementById("filterMeta");
const groupsList = document.getElementById("groupsList");
const searchBox = document.getElementById("searchBox");
const selectAllBtn = document.getElementById("selectAllBtn");
const clearAllBtn = document.getElementById("clearAllBtn");
const runBtn = document.getElementById("runBtn");
const results = document.getElementById("results");

const state = {
  filterId: null,
  groups: [],
};

function setStatus(msg) {
  statusEl.textContent = msg;
}

async function loadLayers() {
  setStatus("Cargando capas...");
  const res = await fetch("/layers");
  const data = await res.json();
  layerSelect.innerHTML = "";
  data.layers.forEach((l) => {
    const opt = document.createElement("option");
    opt.value = l.name;
    opt.textContent = l.name;
    layerSelect.appendChild(opt);
  });
  setStatus("Capas listas");
}

async function loadVariables() {
  const layer = layerSelect.value;
  if (!layer) return;
  setStatus("Cargando variables...");
  const res = await fetch(`/variables?layer=${encodeURIComponent(layer)}`);
  if (!res.ok) {
    setStatus("Error al cargar variables");
    return;
  }
  const data = await res.json();
  state.groups = data.groups || [];
  renderGroups();
  setStatus(`Variables listas (${state.groups.length} grupos)`);
}

function renderGroups() {
  const q = (searchBox.value || "").toLowerCase();
  groupsList.innerHTML = "";
  if (!state.groups.length) {
    groupsList.innerHTML = '<div class="empty">Sin grupos disponibles.</div>';
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "groups";

  state.groups
    .filter((g) => g.group.toLowerCase().includes(q))
    .forEach((group) => {
      const card = document.createElement("div");
      card.className = "group-card";

      const title = document.createElement("div");
      title.className = "group-title";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "group-check";
      checkbox.dataset.group = group.group;
      title.appendChild(checkbox);
      title.appendChild(document.createTextNode(` ${group.group}`));

      const meta = document.createElement("div");
      meta.className = "group-meta";
      meta.textContent = `${group.fields.length} columnas`;

      card.appendChild(title);
      card.appendChild(meta);
      wrapper.appendChild(card);
    });

  groupsList.appendChild(wrapper);
}

filterInput.addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  setStatus("Subiendo filtro...");

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/upload-filter", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    setStatus("Error al cargar filtro");
    filterMeta.textContent = "No se pudo leer el archivo.";
    return;
  }

  const data = await res.json();
  state.filterId = data.filter_id;
  filterMeta.textContent = `Filtro cargado: ${data.rows} filas`;
  setStatus("Filtro listo");
});

loadVarsBtn.addEventListener("click", loadVariables);
searchBox.addEventListener("input", renderGroups);

selectAllBtn.addEventListener("click", () => {
  document.querySelectorAll(".group-check").forEach((c) => (c.checked = true));
});

clearAllBtn.addEventListener("click", () => {
  document.querySelectorAll(".group-check").forEach((c) => (c.checked = false));
});

runBtn.addEventListener("click", async () => {
  if (!state.filterId) {
    setStatus("Carga un filtro primero");
    return;
  }
  const layer = layerSelect.value;
  const selected = Array.from(document.querySelectorAll(".group-check"))
    .filter((c) => c.checked)
    .map((c) => c.dataset.group);
  if (!selected.length) {
    setStatus("Selecciona al menos un grupo");
    return;
  }

  setStatus("Generando reportes...");
  const res = await fetch("/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      layer,
      filter_id: state.filterId,
      groups: selected,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    setStatus("Error al generar");
    results.innerHTML = `<div class="empty">${err}</div>`;
    return;
  }

  const data = await res.json();
  renderResults(data);
  setStatus("Reportes listos");
});

function renderResults(data) {
  results.innerHTML = "";
  const wrapper = document.createElement("div");
  wrapper.className = "results";

  const combined = document.createElement("div");
  combined.className = "result-card";
  combined.innerHTML = `
    <div class="group-title">Salida consolidada</div>
    <div class="group-meta">CSV: <code>${data.combined_csv}</code></div>
    <div class="group-meta">HTML: <code>${data.combined_html}</code></div>
    <div class="group-meta">XLSX: <code>${data.combined_xlsx}</code></div>
    <div class="group-meta">DOCX: <code>${data.combined_docx}</code></div>
    <div class="group-meta">Sugerencia: abrir el DOCX o HTML y copiar a Word.</div>
  `;
  wrapper.appendChild(combined);

  data.reports.forEach((report) => {
    const card = document.createElement("div");
    card.className = "result-card";
    card.innerHTML = `
      <div class="group-title">${report.group_label || report.group}</div>
      <div class="group-meta">Filas: ${report.rows_count}</div>
      <div class="group-meta">CSV: <code>${report.csv_path}</code></div>
    `;
    wrapper.appendChild(card);
  });

  results.appendChild(wrapper);
}

loadLayers();
