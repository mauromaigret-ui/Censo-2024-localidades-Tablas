const statusEl = document.getElementById("status");
const layerSelect = document.getElementById("layerSelect");
const loadVarsBtn = document.getElementById("loadVarsBtn");
const filterInput = document.getElementById("filterInput");
const filterMeta = document.getElementById("filterMeta");
let localityInput = document.getElementById("localityInput");
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

if (!localityInput && filterMeta) {
  const field = document.createElement("div");
  field.className = "field";
  field.innerHTML = `
    <label for="localityInput">Localidad o sector (obligatorio)</label>
    <input type="text" id="localityInput" placeholder="Ej: La Negra" />
  `;
  filterMeta.insertAdjacentElement("afterend", field);
  localityInput = field.querySelector("#localityInput");
}

function setStatus(msg) {
  statusEl.textContent = msg;
}

let layersRetry = 0;
const MAX_LAYER_RETRY = 5;

function applyLayersToSelect(layers) {
  if (!Array.isArray(layers) || !layers.length) {
    return false;
  }
  layerSelect.innerHTML = "";
  layers.forEach((l) => {
    const opt = document.createElement("option");
    opt.value = l.name;
    opt.textContent = l.name;
    layerSelect.appendChild(opt);
  });
  return true;
}

async function loadLayers() {
  try {
    setStatus("Cargando capas...");
    const res = await fetch("/layers");
    if (!res.ok) {
      throw new Error(await res.text());
    }
    const data = await res.json();
    const layers = data.layers || [];
    if (applyLayersToSelect(layers)) {
      localStorage.setItem("layers_cache", JSON.stringify(layers));
      setStatus("Capas listas");
      layersRetry = 0;
      return;
    }
    throw new Error("Sin capas disponibles");
  } catch (error) {
    console.error(error);
    const cached = localStorage.getItem("layers_cache");
    if (cached) {
      try {
        const cachedLayers = JSON.parse(cached);
        if (applyLayersToSelect(cachedLayers)) {
          setStatus("Capas cargadas desde caché");
          return;
        }
      } catch (_) {
        // ignore cache errors
      }
    }
    if (layersRetry < MAX_LAYER_RETRY) {
      layersRetry += 1;
      setStatus(`Reintentando capas (${layersRetry}/${MAX_LAYER_RETRY})...`);
      setTimeout(loadLayers, 1500 * layersRetry);
      return;
    }
    if (!layerSelect.options.length) {
      const defaults = [
        "Entidades_CPV24",
        "Aldeas_CPV24",
        "Limite_Urbano_CPV24",
      ];
      defaults.forEach((name) => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        layerSelect.appendChild(opt);
      });
      setStatus("Capas por defecto cargadas");
      return;
    }
    if (!layerSelect.options.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Error al cargar capas";
      layerSelect.appendChild(opt);
    }
    setStatus("Error al cargar capas");
  }
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
  const localidad = (localityInput.value || "").trim();
  if (!localidad) {
    setStatus("Ingresa la localidad o sector");
    localityInput.focus();
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
      localidad,
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
    <div class="group-meta">XLSX: <code>${data.combined_xlsx}</code></div>
    <div class="group-meta">DOCX: <code>${data.combined_docx}</code></div>
    <div class="group-meta">Sugerencia: abrir el DOCX y copiar a Word.</div>
  `;
  wrapper.appendChild(combined);

  data.reports.forEach((report) => {
    const card = document.createElement("div");
    card.className = "result-card";
    const csvLine = report.csv_path
      ? `<div class="group-meta">CSV: <code>${report.csv_path}</code></div>`
      : "";
    card.innerHTML = `
      <div class="group-title">${report.group_label || report.group}</div>
      <div class="group-meta">Filas: ${report.rows_count}</div>
      ${csvLine}
    `;
    wrapper.appendChild(card);
  });

  results.appendChild(wrapper);
}

loadLayers();
