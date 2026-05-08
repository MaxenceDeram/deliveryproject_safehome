const charts = {};
let currentRange = "6h";
let firstLoad = true;
let lastTimestamp = null;
let pollInFlight = false;

const tones = ["good", "medium", "bad", "unknown", "info"];
const metricSparklineIds = {
  co2: "sparkline-co2",
  temperature: "sparkline-temperature",
  humidity: "sparkline-humidity",
  gas_resistance: "sparkline-gas"
};

function qs(selector, root = document) {
  return root.querySelector(selector);
}

function qsa(selector, root = document) {
  return [...root.querySelectorAll(selector)];
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function getJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`Erreur API ${response.status}`);
  return response.json();
}

function setupTheme() {
  const saved = localStorage.getItem("safehome-theme") || "dark";
  document.documentElement.dataset.theme = saved;
  const button = qs("[data-theme-toggle]");
  if (button) button.textContent = saved === "dark" ? "Mode clair" : "Mode sombre";
  button?.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("safehome-theme", next);
    button.textContent = next === "dark" ? "Mode clair" : "Mode sombre";
  });
}

function setupNavigation() {
  qs("[data-nav-toggle]")?.addEventListener("click", () => {
    qs("[data-nav-links]")?.classList.toggle("open");
  });
}

function showToast(message) {
  const toast = qs("[data-toast]");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => toast.classList.remove("show"), 2800);
}

function formatAge(seconds) {
  if (seconds === null || seconds === undefined) return "Aucune mise à jour";
  if (seconds < 60) return `il y a ${seconds} secondes`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `il y a ${minutes} minutes`;
  return `il y a ${Math.floor(minutes / 60)} heures`;
}

function formatValue(value, fallback = "Non mesuré") {
  if (value === null || value === undefined || value === "") return fallback;
  return value;
}

function chartReady() {
  return typeof Chart !== "undefined";
}

function chartColors() {
  return {
    green: "#22c55e",
    cyan: "#06b6d4",
    blue: "#3b82f6",
    violet: "#8b5cf6",
    orange: "#f59e0b",
    red: "#ef4444",
    grid: "rgba(148, 163, 184, 0.13)",
    text: "#94a3b8",
    card: "rgba(15, 23, 42, 0.72)"
  };
}

function setToneClass(element, tone) {
  if (!element) return;
  element.classList.remove(...tones, "pulse-alert");
  element.classList.add(tone || "unknown");
}

function animateScore(target) {
  const scoreEl = qs("[data-score]");
  const orb = qs("[data-score-orb]");
  const progress = qs("[data-score-progress]");
  if (!scoreEl || !orb || !progress) return;

  if (target === null || target === undefined) {
    scoreEl.textContent = "--";
    orb.style.setProperty("--score-angle", "0deg");
    progress.style.width = "0%";
    return;
  }

  const current = scoreEl.textContent === "--" ? 0 : Number(scoreEl.textContent) || 0;
  const start = performance.now();
  const duration = 900;

  function frame(now) {
    const rawProgress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - rawProgress, 3);
    const value = Math.round(current + (target - current) * eased);
    scoreEl.textContent = value;
    orb.style.setProperty("--score-angle", `${value * 3.6}deg`);
    progress.style.width = `${value}%`;
    if (rawProgress < 1) requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
}

function updateMetricCard(key, metric) {
  const card = qs(`[data-metric-card="${key}"]`);
  if (!card || !metric) return;

  const valueEl = qs("[data-metric-value]", card);
  const unitEl = qs("[data-metric-unit]", card);
  const statusEl = qs("[data-metric-status]", card);

  setToneClass(card, metric.tone);
  if (metric.tone === "bad") card.classList.add("pulse-alert");

  valueEl.textContent = formatValue(metric.value_label);
  unitEl.textContent = metric.measured ? metric.unit || "" : "";
  statusEl.textContent = metric.status_label || "En attente";
  card.setAttribute("aria-label", `${metric.label}: ${metric.value_label} ${metric.unit || ""}, ${metric.status_label}`);
}

function updateCurrent(payload) {
  const raw = payload.raw || {};
  const computed = payload.computed || {};
  const scoreCard = qs("[data-score-card]");
  const score = computed.global_score;

  setToneClass(scoreCard, computed.tone);
  if (computed.risk_level === "high" || computed.tone === "bad") scoreCard?.classList.add("pulse-alert");

  qs("[data-air-status]").textContent = computed.label || "En attente";
  qs("[data-score-caption]").textContent = computed.human_interpretation || "Aucune mesure récente.";
  qs("[data-smiley]").textContent = computed.smiley || "○";
  animateScore(score);

  const metrics = computed.metrics || {};
  ["co2", "temperature", "humidity", "gas_resistance"].forEach((key) => updateMetricCard(key, metrics[key]));

  renderRecommendations(computed.recommendations || []);
  renderRiskSummary(computed.risks || []);
  renderConfidence(computed.confidence || {
    level: computed.confidence_level,
    label: computed.confidence_label,
    explanation: computed.confidence_explanation
  });
  renderSimpleInterpretation(raw, computed);

  if (raw.timestamp && raw.timestamp !== lastTimestamp) {
    if (!firstLoad) showToast("Nouvelle mesure reçue");
    lastTimestamp = raw.timestamp;
  }
}

function renderSimpleInterpretation(raw = {}, computed = {}) {
  const status = qs("[data-simple-status]");
  const message = qs("[data-simple-message]");
  const action = qs("[data-simple-action]");
  const co2Source = qs("[data-co2-source]");
  const pmSource = qs("[data-pm-source]");
  if (!status || !message || !action) return;

  const recommendations = computed.recommendations || [];
  const firstAction = recommendations[0]?.action;
  const score = computed.global_score;
  status.textContent = score === null || score === undefined
    ? "En attente d'une mesure"
    : `${computed.label || "Statut inconnu"} · ${score}/100`;

  if (score === null || score === undefined) {
    message.textContent = "Aucune donnée exploitable n'a encore été reçue par l'API.";
    action.textContent = "Lancez une simulation ou connectez le boîtier SafeHome.";
  } else if (!("co2" in raw)) {
    message.textContent = "Le score utilise le BME680, mais le CO₂ réel n'est pas mesuré dans cette trame.";
    action.textContent = "Ajoutez ou vérifiez le SCD40/SCD41 pour suivre la ventilation.";
  } else if ((computed.risks || []).some((risk) => risk.level === "high")) {
    message.textContent = "Un signal prioritaire demande une action simple et rapide.";
    action.textContent = firstAction || "Aérez la pièce et vérifiez la ventilation.";
  } else if (computed.tone === "medium") {
    message.textContent = "L'air reste utilisable, avec un point de vigilance à suivre.";
    action.textContent = firstAction || "Aérez brièvement et surveillez l'évolution.";
  } else if (computed.tone === "bad") {
    message.textContent = "La qualité de l'air est dégradée selon les mesures disponibles.";
    action.textContent = firstAction || "Aérez immédiatement et réduisez les sources de pollution.";
  } else {
    message.textContent = "L'air est sain selon les mesures reçues. Les données absentes restent non inventées.";
    action.textContent = firstAction || "Gardez vos habitudes de ventilation régulière.";
  }

  if (co2Source) {
    co2Source.textContent = "co2" in raw
      ? `CO₂ réel reçu: ${raw.co2} ppm`
      : "CO₂ non mesuré sans SCD40/SCD41";
  }
  if (pmSource) {
    const hasPm = "pm25" in raw || "pm10" in raw;
    pmSource.textContent = hasPm ? "Particules reçues par capteur dédié" : "Non mesuré sans capteur dédié";
  }
}

function iconSymbol(icon) {
  return {
    window: "▥",
    drop: "◖",
    thermo: "℃",
    wind: "≋",
    sun: "☀",
    leaf: "♧",
    sensor: "◉"
  }[icon] || "•";
}

function priorityTone(priority = "") {
  if (priority === "critique" || priority === "élevée") return "bad";
  if (priority === "moyenne") return "medium";
  return "good";
}

function renderRecommendations(items = []) {
  const list = qs("[data-dashboard-recommendations]");
  if (!list) return;
  const visible = items.slice(0, 4);
  list.innerHTML = visible.length
    ? visible.map((item) => `
      <article class="recommendation-card ${priorityTone(item.priority)} fade-up" tabindex="0">
        <span class="recommendation-icon">${iconSymbol(item.icon)}</span>
        <div>
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.message)}</p>
          <small>${escapeHtml(item.priority)} · ${escapeHtml(item.action)}</small>
        </div>
        <span class="chevron">›</span>
      </article>
    `).join("")
    : `<article class="recommendation-card"><div><strong>En attente</strong><p>Aucune action sans mesure récente.</p></div></article>`;
}

function renderRiskSummary(risks = []) {
  const target = qs("[data-risk-summary]");
  if (!target) return;
  if (!risks.length) {
    target.innerHTML = `<span><small>Statut</small><strong>Aucun signal critique</strong></span><p class="muted">Les publics sensibles doivent rester attentifs au confort et à la ventilation.</p>`;
    return;
  }
  target.innerHTML = risks.slice(0, 3).map((risk) => `
    <span>
      <small>${escapeHtml(risk.level)}</small>
      <strong>${escapeHtml(risk.title)}</strong>
    </span>
  `).join("");
}

function renderConfidence(confidence = {}) {
  const label = qs("[data-confidence-level]");
  const bar = qs("[data-confidence-bar]");
  const text = qs("[data-confidence-text]");
  if (!label || !bar || !text) return;

  const level = confidence.level || "low";
  const percent = { high: 100, good: 82, medium: 58, low: 32 }[level] || 32;
  label.textContent = confidence.label || "Confiance faible";
  bar.style.width = `${percent}%`;
  text.textContent = confidence.explanation || "Mesures incomplètes.";
}

function renderHealth(health) {
  const state = qs("[data-device-state]");
  const apiState = qs("[data-api-state]");
  const lastUpdate = qs("[data-last-update]");
  const wifi = qs("[data-wifi-state]");
  const battery = qs("[data-battery-level]");
  const deviceId = qs("[data-device-id]");

  const isConnected = health.esp32_connected || health.last_source === "simulation";
  state?.classList.toggle("offline", !isConnected);
  state?.classList.toggle("simulation", health.last_source === "simulation");
  if (qs("strong", state)) {
    qs("strong", state).textContent = health.esp32_connected
      ? "Appareil connecté"
      : health.last_source === "simulation"
        ? "Mode simulation"
        : "Hors ligne";
  }
  if (apiState) {
    apiState.classList.toggle("connected", health.api === "ok");
    const apiLabel = qs("[data-api-label]", apiState);
    if (apiLabel) apiLabel.textContent = health.api === "ok" ? "En ligne" : "API indisponible";
  }
  qs("[data-simulation-state]")?.classList.toggle("is-hidden", health.last_source !== "simulation");
  if (lastUpdate) lastUpdate.textContent = formatAge(health.last_update_seconds_ago);
  if (wifi) wifi.textContent = health.wifi || "--";
  if (battery) battery.textContent = health.battery === null || health.battery === undefined ? "--" : `${health.battery}%`;
  if (deviceId) deviceId.textContent = health.device_id || "SafeHome Device #1";
}

function makeGradient(ctx, color) {
  const gradient = ctx.createLinearGradient(0, 0, 0, 280);
  gradient.addColorStop(0, `${color}55`);
  gradient.addColorStop(1, `${color}00`);
  return gradient;
}

function renderMeasurementsChart(items = []) {
  const canvas = document.getElementById("measurementsChart");
  if (!canvas || !chartReady()) return;
  const c = chartColors();
  const ctx = canvas.getContext("2d");
  const data = {
    labels: items.map((item) => item.label),
    datasets: [
      {
        label: "CO₂ (ppm)",
        data: items.map((item) => item.co2 ?? null),
        borderColor: c.green,
        backgroundColor: makeGradient(ctx, c.green),
        fill: true,
        tension: 0.42,
        borderWidth: 3,
        pointRadius: 0,
        yAxisID: "y"
      },
      {
        label: "Température (°C)",
        data: items.map((item) => item.temperature ?? null),
        borderColor: c.violet,
        backgroundColor: "transparent",
        tension: 0.42,
        borderWidth: 2,
        pointRadius: 0,
        yAxisID: "y1"
      },
      {
        label: "Humidité (%)",
        data: items.map((item) => item.humidity ?? null),
        borderColor: c.blue,
        backgroundColor: "transparent",
        tension: 0.42,
        borderWidth: 2,
        pointRadius: 0,
        yAxisID: "y1"
      },
      {
        label: "COV (IAQ)",
        data: items.map((item) => item.voc_index ?? null),
        borderColor: c.orange,
        backgroundColor: "transparent",
        tension: 0.42,
        borderWidth: 2,
        pointRadius: 0,
        yAxisID: "y1"
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 900, easing: "easeOutQuart" },
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "rgba(2, 6, 23, 0.94)",
        borderColor: "rgba(148, 163, 184, 0.22)",
        borderWidth: 1,
        padding: 12,
        titleColor: "#f8fafc",
        bodyColor: "#cbd5e1"
      }
    },
    scales: {
      x: { grid: { color: c.grid }, ticks: { color: c.text, maxRotation: 0, autoSkip: true } },
      y: {
        beginAtZero: false,
        grid: { color: c.grid },
        ticks: { color: c.text },
        title: { display: false }
      },
      y1: {
        position: "right",
        beginAtZero: true,
        max: 100,
        grid: { drawOnChartArea: false },
        ticks: { color: c.text }
      }
    }
  };

  if (!charts.measurements) charts.measurements = new Chart(canvas, { type: "line", data, options });
  else {
    charts.measurements.data = data;
    charts.measurements.options = options;
    charts.measurements.update();
  }
}

function renderSparkline(key, items = []) {
  const id = metricSparklineIds[key];
  const canvas = document.getElementById(id);
  if (!canvas || !chartReady()) return;
  const c = chartColors();
  const field = key === "gas_resistance" ? "voc_index" : key;
  const color = { co2: c.violet, temperature: c.cyan, humidity: c.blue, gas_resistance: c.orange }[key] || c.green;
  const data = {
    labels: items.map((item) => item.label),
    datasets: [{
      data: items.map((item) => item[field] ?? null),
      borderColor: color,
      backgroundColor: "transparent",
      tension: 0.45,
      pointRadius: 0,
      borderWidth: 2
    }]
  };
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    scales: { x: { display: false }, y: { display: false } }
  };
  if (!charts[id]) charts[id] = new Chart(canvas, { type: "line", data, options });
  else {
    charts[id].data = data;
    charts[id].update("none");
  }
}

function qualityDistribution(items = []) {
  const buckets = [
    { label: "Excellente", tone: "excellent", count: 0, color: "#22c55e" },
    { label: "Bonne", tone: "good", count: 0, color: "#a3e635" },
    { label: "Vigilance", tone: "medium", count: 0, color: "#f59e0b" },
    { label: "Dégradée", tone: "bad", count: 0, color: "#ef4444" }
  ];
  items.forEach((item) => {
    const score = item.score;
    if (score === null || score === undefined) return;
    if (score >= 85) buckets[0].count += 1;
    else if (score >= 70) buckets[1].count += 1;
    else if (score >= 50) buckets[2].count += 1;
    else buckets[3].count += 1;
  });
  return buckets;
}

function renderDonut(items = []) {
  const canvas = document.getElementById("qualityDonut");
  const legend = qs("[data-donut-legend]");
  if (!canvas || !chartReady()) return;
  const buckets = qualityDistribution(items);
  const total = buckets.reduce((sum, bucket) => sum + bucket.count, 0) || 1;
  const data = {
    labels: buckets.map((bucket) => bucket.label),
    datasets: [{
      data: buckets.map((bucket) => bucket.count),
      backgroundColor: buckets.map((bucket) => bucket.color),
      borderColor: "rgba(2, 6, 23, 0.96)",
      borderWidth: 4,
      hoverOffset: 4
    }]
  };
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "70%",
    plugins: { legend: { display: false }, tooltip: { enabled: true } }
  };
  if (!charts.donut) charts.donut = new Chart(canvas, { type: "doughnut", data, options });
  else {
    charts.donut.data = data;
    charts.donut.update();
  }
  if (legend) {
    legend.innerHTML = buckets.map((bucket) => `
      <span><i style="background:${bucket.color}"></i>${bucket.label}<strong>${Math.round((bucket.count / total) * 100)}%</strong></span>
    `).join("");
  }
}

function renderDailySummary(summary = {}) {
  const target = qs("[data-daily-summary]");
  if (!target) return;
  if (!summary.count) {
    target.innerHTML = `<p class="muted">Aucune mesure sur 24h.</p>`;
    return;
  }
  target.innerHTML = `
    <span><small>CO₂ moyen</small><strong>${formatValue(summary.co2_avg)} ppm</strong></span>
    <span><small>Température moyenne</small><strong>${formatValue(summary.temperature_avg)} °C</strong></span>
    <span><small>Humidité moyenne</small><strong>${formatValue(summary.humidity_avg)} %</strong></span>
    <span><small>Pic COV</small><strong>${formatValue(summary.voc_peak, "--")} IAQ</strong></span>
  `;
}

async function loadDashboardHistory(range = currentRange) {
  if (!qs("[data-dashboard-app]")) return;
  if (!chartReady()) {
    window.setTimeout(() => loadDashboardHistory(range), 120);
    return;
  }
  const data = await getJson(`/api/history?range=${range}`);
  const items = data.items || [];
  renderMeasurementsChart(items);
  ["co2", "temperature", "humidity", "gas_resistance"].forEach((key) => renderSparkline(key, items));
  renderDonut(items);
  renderDailySummary(data.summary || {});
}

async function refreshDashboard() {
  if (!qs("[data-dashboard-app]")) return;
  const [current, health] = await Promise.all([
    getJson("/api/current-data"),
    getJson("/api/health")
  ]);
  updateCurrent(current);
  renderHealth(health);
  await loadDashboardHistory(currentRange);
  const appShell = qs("[data-dashboard-app]");
  appShell?.classList.remove("is-loading");
  appShell?.setAttribute("aria-busy", "false");
  firstLoad = false;
}

function setupDashboardRange() {
  qsa("[data-dashboard-range]").forEach((button) => {
    button.addEventListener("click", async () => {
      qsa("[data-dashboard-range]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      currentRange = button.dataset.dashboardRange;
      await loadDashboardHistory(currentRange);
    });
  });
}

function setupSimulation() {
  qsa("[data-simulate]").forEach((button) => {
    button.addEventListener("click", async () => {
      const previous = button.textContent;
      button.disabled = true;
      button.textContent = "Simulation...";
      try {
        await getJson("/api/simulate");
        await refreshDashboard();
        await loadLegacyHistory();
        await loadRecommendationsPage();
        showToast("Mesure simulée créée");
      } finally {
        button.disabled = false;
        button.textContent = previous;
      }
    });
  });
}

function legacyChartOptions(label, color) {
  return {
    type: "line",
    data: { labels: [], datasets: [{ label, data: [], borderColor: color, backgroundColor: `${color}22`, tension: 0.35, fill: true, pointRadius: 2 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#94a3b8" } },
        y: { grid: { color: "rgba(148, 163, 184, 0.16)" }, ticks: { color: "#94a3b8" } }
      }
    }
  };
}

function renderLegacyCharts(items) {
  const configs = {
    gasChart: ["COV estimés", "#f59e0b", "voc_index"],
    humidityChart: ["Humidité", "#3b82f6", "humidity"],
    temperatureChart: ["Température", "#06b6d4", "temperature"],
    scoreChart: ["Score global", "#22c55e", "score"]
  };
  Object.entries(configs).forEach(([id, [label, color, field]]) => {
    const canvas = document.getElementById(id);
    if (!canvas || !chartReady()) return;
    if (!charts[id]) charts[id] = new Chart(canvas, legacyChartOptions(label, color));
    charts[id].data.labels = items.map((item) => item.label);
    charts[id].data.datasets[0].data = items.map((item) => item[field] ?? null);
    charts[id].update();
  });
}

async function loadLegacyHistory(range = "24h") {
  if (!document.getElementById("gasChart")) return;
  if (!chartReady()) {
    window.setTimeout(() => loadLegacyHistory(range), 120);
    return;
  }
  const data = await getJson(`/api/history?range=${range}`);
  renderLegacyCharts(data.items || []);
  const summary = qs("[data-history-summary]");
  if (summary) {
    summary.textContent = data.count
      ? `${data.count} mesure(s). Dernier score: ${data.items.at(-1)?.score ?? "--"}/100.`
      : "Aucune mesure enregistrée pour cette période.";
  }
}

function setupHistoryFilters() {
  qsa("[data-range]").forEach((button) => {
    button.addEventListener("click", async () => {
      qsa("[data-range]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      await loadLegacyHistory(button.dataset.range);
    });
  });
}

function recommendationPageCard(item) {
  return `
    <article class="recommendation-card ${priorityTone(item.priority)} fade-up" tabindex="0">
      <span class="recommendation-icon">${iconSymbol(item.icon)}</span>
      <div>
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.message)}</p>
        <small>${escapeHtml(item.action)}</small>
      </div>
      <span class="chevron">›</span>
    </article>
  `;
}

async function loadRecommendationsPage() {
  const grid = qs("[data-recommendations-grid]");
  if (!grid) return;
  const data = await getJson("/api/recommendations");
  const status = qs("[data-recommendation-status]");
  if (status) status.textContent = `${data.smiley || "○"} ${data.label || "En attente"} · score ${data.score ?? "--"}/100`;
  grid.innerHTML = (data.items || []).map(recommendationPageCard).join("");
}

async function loadGuidelines() {
  const grid = qs("[data-guidelines-list]");
  if (!grid) return;
  const data = await getJson("/api/guidelines");
  const order = ["co2", "humidity", "temperature", "gas_resistance", "pm25", "pm10", "co", "no2"];
  grid.innerHTML = order.map((key) => {
    const guideline = data.guidelines[key];
    if (!guideline) return "";
    return `
      <article class="reference-card fade-up" tabindex="0">
        <h3>${escapeHtml(guideline.label)}</h3>
        <p>${escapeHtml(guideline.human_explanation)}</p>
        <small>${escapeHtml(guideline.source)}</small>
      </article>
    `;
  }).join("");
}

function setupFadeObserver() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add("is-visible");
    });
  }, { threshold: 0.08 });

  const observe = () => {
    qsa(".fade-up:not(.is-observed)").forEach((item, index) => {
      item.classList.add("is-observed");
      item.style.transitionDelay = `${Math.min(index * 35, 220)}ms`;
      observer.observe(item);
    });
  };

  observe();
  new MutationObserver(observe).observe(document.body, { childList: true, subtree: true });
}

document.addEventListener("DOMContentLoaded", async () => {
  setupTheme();
  setupNavigation();
  setupSimulation();
  setupDashboardRange();
  setupHistoryFilters();
  setupFadeObserver();

  try {
    await refreshDashboard();
    await loadLegacyHistory();
    await loadRecommendationsPage();
    await loadGuidelines();
  } catch (error) {
    showToast("Impossible de charger l'API SafeHome");
  }

  if (qs("[data-dashboard-app]")) {
    window.setInterval(async () => {
      if (pollInFlight) return;
      pollInFlight = true;
      try {
        await refreshDashboard();
      } finally {
        pollInFlight = false;
      }
    }, 10000);
  }
});
