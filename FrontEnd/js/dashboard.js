// js/dashboard.js
// ====================== CONFIG / INIT ======================

// Pastikan config.js sudah di-load duluan
if (typeof window.API_BASE === "undefined") {
  console.error(
    "[DASHBOARD] API_BASE is not defined. Make sure config.js is loaded before dashboard.js"
  );
}
const API_BASE = window.API_BASE;

// Interval auto-refresh (ms)
const STATUS_INTERVAL_MS = 5000;
const HISTORY_INTERVAL_MS = 10000;
const LOGS_INTERVAL_MS = 8000;

// Global chart instance
let sensorChart = null;

document.addEventListener("DOMContentLoaded", () => {
  console.log("[DASHBOARD] script loaded, API_BASE =", API_BASE);
  attachEventHandlers();
  refreshAll();

  // Auto refresh
  setInterval(fetchStatus, STATUS_INTERVAL_MS);
  setInterval(fetchHistory, HISTORY_INTERVAL_MS);
  setInterval(fetchLogs, LOGS_INTERVAL_MS);
});

function attachEventHandlers() {
  // Pump buttons
  const btnPumpOn = document.getElementById("btn-pump-on");
  const btnPumpOff = document.getElementById("btn-pump-off");
  if (btnPumpOn) btnPumpOn.addEventListener("click", () => setPump("on"));
  if (btnPumpOff) btnPumpOff.addEventListener("click", () => setPump("off"));

  // Servo buttons
  const btnServoOpen = document.getElementById("btn-servo-open");
  const btnServoHalf = document.getElementById("btn-servo-half");
  const btnServoClose = document.getElementById("btn-servo-close");
  if (btnServoOpen) btnServoOpen.addEventListener("click", () => setServo("open"));
  if (btnServoHalf) btnServoHalf.addEventListener("click", () => setServo("half"));
  if (btnServoClose) btnServoClose.addEventListener("click", () => setServo("close"));

  // Schedule form
  const scheduleForm = document.getElementById("schedule-form");
  if (scheduleForm) {
    scheduleForm.addEventListener("submit", (e) => {
      e.preventDefault();
      saveScheduleFromForm();
    });
  }
}

function refreshAll() {
  fetchStatus();
  fetchHistory();
  fetchLogs();
  fetchSchedule(); // prefill schedule form
}


// ====================== FETCH HELPERS ======================

async function fetchJSON(path, options = {}) {
  try {
    const res = await fetch(API_BASE + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      console.error("API error", path, res.status);
      showToast(`API error ${res.status} on ${path}`, "error");
      return null;
    }
    return await res.json();
  } catch (err) {
    console.error("Network error", path, err);
    showToast(`Network error on ${path}`, "error");
    return null;
  }
}


// ====================== STATUS ======================

async function fetchStatus() {
  console.log("[DASHBOARD] fetching /api/status ...");
  const data = await fetchJSON("/api/status");
  console.log("[DASHBOARD] status response =", data);
  if (!data) return;
  updateStatusUI(data);
}

function updateStatusUI(status) {
  const sensor = status.sensor || {};
  const schedule = status.schedule || {};

  // ---- KPI: sensor values ----
  setKpiValue("temp-value", sensor.temperature, 1);
  setKpiValue("humidity-value", sensor.humidity, 1);
  setKpiValue("soil-value", sensor.soil_moisture, 0);
  setKpiValue("light-value", sensor.light, 0);

  // ---- Pump / Servo pills ----
  updateStatusPill(
    document.getElementById("pump-status-pill"),
    status.pump_status === "on" ? "Pump ON" : "Pump OFF",
    status.pump_status === "on"
  );

  let servoLabel = "Servo Closed";
  if (status.servo_position === "open") servoLabel = "Servo Open";
  else if (status.servo_position === "half") servoLabel = "Servo Half";

  updateStatusPill(
    document.getElementById("servo-status-pill"),
    servoLabel,
    status.servo_position !== "close"
  );

  // ---- Last update time ----
  const ts = sensor.timestamp;
  const lastEl = document.getElementById("last-update");
  if (lastEl) {
    lastEl.textContent = ts ? formatTimestampShort(ts) : "—";
  }

  // ---- Schedule summary ----
  const schedEl = document.getElementById("schedule-summary");
  if (schedEl && schedule) {
    if (schedule.enabled) {
      schedEl.textContent =
        `Enabled • ${schedule.time_hhmm}, ` +
        `duration ${schedule.duration_seconds}s, ` +
        `threshold ${schedule.moisture_threshold}`;
    } else {
      schedEl.textContent = "Disabled";
    }
  }
}

function setKpiValue(elementId, value, digits = 0) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (value == null || Number.isNaN(value)) {
    el.textContent = "-";
  } else {
    el.textContent = Number(value).toFixed(digits);
  }
}

function updateStatusPill(el, label, isActive) {
  if (!el) return;
  el.textContent = label;
  el.classList.toggle("pill-on", isActive);
  el.classList.toggle("pill-off", !isActive);
}

function setConnectionStatus(isConnected) {
  const container = document.querySelector(".connection-indicator");
  const textEl = document.getElementById("connection-text");

  if (!container || !textEl) return;

  if (isConnected) {
    container.classList.add("connected");
    container.classList.remove("disconnected");
    textEl.textContent = "Connected";
  } else {
    container.classList.add("disconnected");
    container.classList.remove("connected");
    textEl.textContent = "Disconnected";
  }
}

// ====================== HISTORY (CHART) ======================

async function fetchHistory() {
  const data = await fetchJSON("/api/history?limit=50");
  if (!data) return;
  updateHistoryChart(data);
}

function updateHistoryChart(history) {
  const canvas = document.getElementById("sensor-chart");
  if (!canvas || typeof Chart === "undefined") {
    // Chart.js tidak ada / canvas tidak ditemukan
    return;
  }

  // history dari API kirim DESC, kita balik
  const sorted = [...history].reverse();

  const labels = sorted.map((row) => formatTimeLabel(row.timestamp || ""));
  const tempData = sorted.map((row) => row.temperature ?? null);
  const humData = sorted.map((row) => row.humidity ?? null);
  const soilData = sorted.map((row) => row.soil_moisture ?? null);
  const lightData = sorted.map((row) => row.light ?? null);

  const datasets = [
    {
      label: "Temperature (°C)",
      data: tempData,
      borderWidth: 2,
      tension: 0.2,
      yAxisID: "y1",
    },
    {
      label: "Humidity (%)",
      data: humData,
      borderWidth: 2,
      tension: 0.2,
      yAxisID: "y1",
    },
    {
      label: "Soil Moisture",
      data: soilData,
      borderWidth: 2,
      tension: 0.2,
      yAxisID: "y2",
    },
    {
      label: "Light",
      data: lightData,
      borderWidth: 1,
      borderDash: [4, 4],
      tension: 0.2,
      yAxisID: "y2",
    },
  ];

  if (sensorChart) {
    sensorChart.data.labels = labels;
    sensorChart.data.datasets = datasets;
    sensorChart.update();
  } else {
    sensorChart = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        scales: {
          y1: {
            type: "linear",
            position: "left",
            title: { display: true, text: "Temp / Humidity" },
          },
          y2: {
            type: "linear",
            position: "right",
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Soil / Light (raw)" },
          },
        },
        plugins: {
          legend: {
            display: true,
          },
        },
      },
    });
  }
}


// ====================== LOGS ======================

async function fetchLogs() {
  const data = await fetchJSON("/api/logs?limit=50");
  if (!data) return;
  updateLogsTable(data);
}

function updateLogsTable(logs) {
  const tbody = document.getElementById("logs-tbody");
  if (!tbody) return;

  tbody.innerHTML = "";

  logs.forEach((log) => {
    const tr = document.createElement("tr");

    const tdTime = document.createElement("td");
    tdTime.textContent = formatTimestampShort(log.timestamp);
    tr.appendChild(tdTime);

    const tdSource = document.createElement("td");
    tdSource.textContent = log.source || "-";
    tr.appendChild(tdSource);

    const tdPump = document.createElement("td");
    tdPump.textContent = log.pump_status ?? "—";
    tr.appendChild(tdPump);

    const tdServo = document.createElement("td");
    tdServo.textContent = log.servo_position ?? "—";
    tr.appendChild(tdServo);

    const tdMsg = document.createElement("td");
    tdMsg.textContent = log.message || "";
    tr.appendChild(tdMsg);

    tbody.appendChild(tr);
  });
}


// ====================== PUMP / SERVO CONTROL ======================

async function setPump(status) {
  showToast(`Sending pump ${status.toUpperCase()}...`, "info");
  const res = await fetchJSON("/api/pump", {
    method: "POST",
    body: JSON.stringify({ status }),
  });
  if (res && res.ok) {
    showToast(`Pump ${status.toUpperCase()} command queued`, "success");
    fetchLogs();
    fetchStatus();
  }
}

async function setServo(position) {
  showToast(`Moving servo to ${position}...`, "info");
  const res = await fetchJSON("/api/servo", {
    method: "POST",
    body: JSON.stringify({ position }),
  });
  if (res && res.ok) {
    showToast(`Servo "${position}" command queued`, "success");
    fetchLogs();
    fetchStatus();
  }
}


// ====================== SCHEDULE ======================

async function fetchSchedule() {
  const sched = await fetchJSON("/api/schedule");
  if (!sched) return;
  fillScheduleForm(sched);
}

function fillScheduleForm(sched) {
  const enabledEl = document.getElementById("schedule-enabled");
  const timeEl = document.getElementById("schedule-time");
  const durEl = document.getElementById("schedule-duration");
  const thrEl = document.getElementById("schedule-threshold");

  if (enabledEl) enabledEl.checked = !!sched.enabled;
  if (timeEl && sched.time_hhmm) timeEl.value = sched.time_hhmm;
  if (durEl && sched.duration_seconds != null) durEl.value = sched.duration_seconds;
  if (thrEl && sched.moisture_threshold != null) thrEl.value = sched.moisture_threshold;
}

async function saveScheduleFromForm() {
  const enabledEl = document.getElementById("schedule-enabled");
  const timeEl = document.getElementById("schedule-time");
  const durEl = document.getElementById("schedule-duration");
  const thrEl = document.getElementById("schedule-threshold");

  const payload = {
    enabled: enabledEl ? enabledEl.checked : false,
    time_hhmm: timeEl ? timeEl.value || "06:00" : "06:00",
    duration_seconds: durEl ? Number(durEl.value || 30) : 30,
    moisture_threshold: thrEl ? Number(thrEl.value || 300) : 300,
  };

  showToast("Saving schedule...", "info");
  const res = await fetchJSON("/api/schedule", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (res && res.ok) {
    showToast("Schedule saved", "success");
    fetchStatus();
  }
}


// ====================== UTILITIES ======================

function formatTimestampShort(ts) {
  if (!ts) return "—";
  // backend default: "YYYY-MM-DD HH:MM:SS"
  const d = new Date(ts.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return ts; // fallback
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function formatTimeLabel(ts) {
  if (!ts) return "";
  return formatTimestampShort(ts);
}

// Simple toast (optional – sesuaikan dengan HTML/CSS kamu)
function showToast(message, type = "info") {
  const el = document.getElementById("toast");
  if (!el) {
    console.log("[TOAST]", type, message);
    return;
  }
  el.textContent = message;
  el.className = ""; // reset
  el.classList.add("toast", `toast-${type}`);
  el.style.opacity = "1";
  setTimeout(() => {
    el.style.opacity = "0";
  }, 2500);
}
