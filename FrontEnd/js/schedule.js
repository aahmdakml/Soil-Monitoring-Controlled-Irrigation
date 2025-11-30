// schedule.js

const formSchedule = document.getElementById("schedule-form");
const inputEnabled = document.getElementById("sched-enabled");
const inputTime = document.getElementById("sched-time");
const inputDuration = document.getElementById("sched-duration");
const inputMoist = document.getElementById("sched-moisture");

async function loadSchedule() {
  try {
    const sched = await apiGet("/api/schedule");
    if (!sched) return;
    inputEnabled.checked = !!sched.enabled;
    if (sched.time_hhmm) inputTime.value = sched.time_hhmm;
    if (sched.duration_seconds != null) inputDuration.value = sched.duration_seconds;
    if (sched.moisture_threshold != null) inputMoist.value = sched.moisture_threshold;
  } catch (err) {
    console.error("Error loadSchedule:", err);
  }
}

async function saveSchedule(event) {
  event.preventDefault();
  try {
    const payload = {
      enabled: inputEnabled.checked,
      time_hhmm: inputTime.value,
      duration_seconds: Number(inputDuration.value),
      moisture_threshold: Number(inputMoist.value),
    };

    await apiPost("/api/schedule", payload);
    alert("Schedule updated");
  } catch (err) {
    console.error("Error saveSchedule:", err);
    alert("Failed to update schedule: " + err.message);
  }
}

if (formSchedule) {
  formSchedule.addEventListener("submit", saveSchedule);
}

window.addEventListener("load", () => {
  loadSchedule();
});
