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
  const btnServoHalf = document. getElementById("btn-servo-half");
  const btnServoClose = document.getElementById("btn-servo-close");
  if (btnServoOpen) btnServoOpen.addEventListener("click", () => setServo("open"));
  if (btnServoHalf) btnServoHalf.addEventListener("click", () => setServo("half"));
  if (btnServoClose) btnServoClose.addEventListener("click", () => setServo("close"));

  // Schedule form
  const scheduleForm = document. getElementById("schedule-form");
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
      setConnectionStatus(false); // 🔥 UPDATE: Set disconnected on error
      return null;
    }
    setConnectionStatus(true); // 🔥 UPDATE: Set connected on success
    return await res.json();
  } catch (err) {
    console.error("Network error", path, err);
    showToast(`Network error on ${path}`, "error");
    setConnectionStatus(false); // 🔥 UPDATE: Set disconnected on network error
    return null;
  }
}


// ====================== STATUS ======================

async function fetchStatus() {
  console.log("[DASHBOARD] fetching /api/status .. .");
  const data = await fetchJSON("/api/status");
  console.log("[DASHBOARD] status response =", data);
  if (!data) return;
  updateStatusUI(data);
}

function updateStatusUI(status) {
  const sensor = status.sensor || {};
  const schedule = status.schedule || {};

  // ---- KPI:  sensor values ----
  setKpiValue("temp-value", sensor.temperature, 1);
  setKpiValue("humidity-value", sensor.humidity, 1);
  setKpiValue("soil-value", sensor.soil_moisture, 0);
  setKpiValue("light-value", sensor.light, 0);

  // ---- Device State:  Pump & Servo ----
  // 🔥 UPDATE: Handle null values, ambil dari status atau fallback ke "-"
  const pumpStatus = status.pump_status || status.last_pump_status || "-";
  const servoPosition = status. servo_position || status.last_servo_position || "-";

  const pumpEl = document.getElementById("pump-status");
  if (pumpEl) {
    pumpEl.textContent = pumpStatus === "-" ? "-" : pumpStatus. toUpperCase();
    pumpEl.className = "badge";
    if (pumpStatus === "on") {
      pumpEl.classList.add("badge-success");
    } else if (pumpStatus === "off") {
      pumpEl.classList.add("badge-neutral");
    } else {
      pumpEl. classList.add("badge-neutral");
    }
  }

  const servoEl = document. getElementById("servo-status");
  if (servoEl) {
    servoEl.textContent = servoPosition === "-" ? "-" : servoPosition;
    servoEl.className = "badge";
    if (servoPosition === "open") {
      servoEl.classList.add("badge-success");
    } else if (servoPosition === "half") {
      servoEl.classList.add("badge-warning");
    } else if (servoPosition === "close") {
      servoEl.classList.add("badge-neutral");
    } else {
      servoEl.classList.add("badge-neutral");
    }
  }

  // ---- Last update time ----
  const ts = sensor.timestamp;
  const lastEl = document.getElementById("last-update");
  if (lastEl) {
    lastEl.textContent = ts ?  formatTimestampShort(ts) : "—";
  }

  // ---- Schedule summary ---- (jika ada element schedule-summary)
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
  if (! el) return;
  if (value == null || Number.isNaN(value)) {
    el.textContent = "-";
  } else {
    el.textContent = Number(value).toFixed(digits);
  }
}

// 🔥 UPDATE: Fix connection status to use correct element
function setConnectionStatus(isConnected) {
  const statusEl = document.getElementById("backend-status");
  if (!statusEl) return;

  if (isConnected) {
    statusEl.textContent = "● Connected";
    statusEl.classList.remove("pill-soft");
    statusEl.classList.add("pill-success");
  } else {
    statusEl.textContent = "● Disconnected";
    statusEl.classList.remove("pill-success");
    statusEl.classList.add("pill-soft");
  }
}

// ====================== HISTORY (CHART) ======================

async function fetchHistory() {
  const data = await fetchJSON("/api/history? limit=50");
  if (!data) return;
  updateHistoryChart(data);
}

function updateHistoryChart(history) {
  const canvas = document.getElementById("sensor-chart"); // 🔥 Pastikan ID ini match dengan HTML
  if (!canvas || typeof Chart === "undefined") {
    console.warn("[CHART] Canvas not found or Chart.js not loaded");
    return;
  }

  const sorted = [... history].reverse();

  const labels = sorted.map((row) => formatTimeLabel(row.timestamp || ""));
  const tempData = sorted.map((row) => row.temperature ??  null);
  const humData = sorted.map((row) => row.humidity ?? null);
  const soilData = sorted.map((row) => row.soil_moisture ?? null);
  const lightData = sorted.map((row) => row.light ??  null);

  const datasets = [
    {
      label: "Temperature (°C)",
      data: tempData,
      borderColor: "rgb(255, 99, 132)",
      backgroundColor: "rgba(255, 99, 132, 0.1)",
      borderWidth: 2,
      tension: 0.3,
      yAxisID: "y1",
    },
    {
      label: "Humidity (%)",
      data: humData,
      borderColor: "rgb(54, 162, 235)",
      backgroundColor: "rgba(54, 162, 235, 0.1)",
      borderWidth: 2,
      tension: 0.3,
      yAxisID: "y1",
    },
    {
      label: "Soil Moisture (ADC)",
      data: soilData,
      borderColor: "rgb(75, 192, 192)",
      backgroundColor: "rgba(75, 192, 192, 0.1)",
      borderWidth: 2,
      tension: 0.3,
      yAxisID: "y2",
    },
    {
      label: "Light (ADC)",
      data: lightData,
      borderColor: "rgb(255, 205, 86)",
      backgroundColor: "rgba(255, 205, 86, 0.1)",
      borderWidth: 1,
      borderDash: [4, 4],
      tension:  0.3,
      yAxisID: "y2",
    },
  ];

  if (sensorChart) {
    // Update existing chart
    sensorChart. data.labels = labels;
    sensorChart.data.datasets = datasets;
    sensorChart.update();
  } else {
    // Create new chart
    sensorChart = new Chart(canvas. getContext("2d"), {
      type: "line",
      data: { labels, datasets },
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
            title:  { display: true, text: "Temp (°C) / Humidity (%)" },
            grid: { color: "rgba(255,255,255,0.1)" },
          },
          y2: {
            type: "linear",
            position: "right",
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Soil / Light (ADC)" },
          },
        },
        plugins:  {
          legend: {
            display: true,
            position: "top",
          },
          tooltip: {
            enabled: true,
            mode: "index",
            intersect: false,
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
  const tbody = document.getElementById("logs-body");
  if (!tbody) return;

  tbody.innerHTML = "";

  if (! logs || logs.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5;
    td.className = "placeholder";
    td.textContent = "No logs yet. ";
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }

  logs.forEach((log) => {
    const tr = document.createElement("tr");

    const tdTime = document.createElement("td");
    tdTime.textContent = formatTimestampShort(log.timestamp);
    tr.appendChild(tdTime);

    const tdPump = document.createElement("td");
    tdPump.textContent = log.pump_status ??  "—";
    tr.appendChild(tdPump);

    const tdServo = document.createElement("td");
    tdServo.textContent = log.servo_position ??  "—";
    tr.appendChild(tdServo);

    const tdSource = document.createElement("td");
    tdSource.textContent = log.source || "-";
    tr.appendChild(tdSource);

    const tdMsg = document.createElement("td");
    tdMsg.textContent = log.message || "";
    tr.appendChild(tdMsg);

    tbody.appendChild(tr);
  });
}


// ====================== PUMP / SERVO CONTROL ======================

async function setPump(status) {
  showToast(`Sending pump ${status. toUpperCase()}... `, "info");
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
  showToast(`Moving servo to ${position}... `, "info");
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
  const enabledEl = document.getElementById("sched-enabled");
  const timeEl = document.getElementById("sched-time");
  const durEl = document.getElementById("sched-duration");
  const thrEl = document.getElementById("sched-moisture");

  if (enabledEl) enabledEl.checked = !!sched.enabled;
  if (timeEl && sched.time_hhmm) timeEl.value = sched.time_hhmm;
  if (durEl && sched.duration_seconds != null) durEl.value = sched.duration_seconds;
  if (thrEl && sched. moisture_threshold != null) thrEl.value = sched.moisture_threshold;
}

async function saveScheduleFromForm() {
  const enabledEl = document.getElementById("sched-enabled");
  const timeEl = document.getElementById("sched-time");
  const durEl = document.getElementById("sched-duration");
  const thrEl = document.getElementById("sched-moisture");

  const payload = {
    enabled: enabledEl ?  enabledEl.checked : false,
    time_hhmm: timeEl ?  timeEl.value || "06:00" : "06:00",
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
  if (! ts) return "—";
  // backend default:  "YYYY-MM-DD HH: MM: SS"
  const d = new Date(ts. replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return ts; // fallback
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d. getMinutes()).padStart(2, "0");
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