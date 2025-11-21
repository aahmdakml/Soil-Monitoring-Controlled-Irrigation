<?php
// monitoring.php
// Tidak ada logika backend di versi ini — seluruh simulasi tetap dijalankan di sisi klien (JavaScript)
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoring Irigasi Kangkung</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header p { font-size: 1.1em; opacity: 0.9; }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }
        .card {
            background: white; border-radius: 15px; padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); transition: transform 0.3s ease;
        }
        .card:hover { transform: translateY(-5px); }
        .card-header { display: flex; align-items: center; margin-bottom: 20px; }
        .card-icon {
            width: 50px; height: 50px; border-radius: 10px; display: flex;
            align-items: center; justify-content: center; font-size: 24px; margin-right: 15px;
        }
        .card-title { font-size: 1.1em; color: #333; font-weight: 600; }
        .card-value { font-size: 2.5em; font-weight: bold; color: #667eea; margin-bottom: 10px; }
        .card-status {
            padding: 8px 15px; border-radius: 20px; font-size: 0.9em;
            display: inline-block; font-weight: 600;
        }
        .status-good { background: #d4edda; color: #155724; }
        .status-warning { background: #fff3cd; color: #856404; }
        .status-danger { background: #f8d7da; color: #721c24; }
        .status-active { background: #cce5ff; color: #004085; }
        .irrigation-schedule {
            background: white; border-radius: 15px; padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); margin-bottom: 30px;
        }
        .schedule-title { font-size: 1.5em; color: #333; margin-bottom: 20px; font-weight: 600; }
        .schedule-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;
        }
        .schedule-item {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px; border-radius: 10px; text-align: center;
        }
        .schedule-time { font-size: 1.8em; font-weight: bold; margin-bottom: 5px; }
        .schedule-label { opacity: 0.9; font-size: 0.9em; }
        .schedule-done { opacity: 0.6; position: relative; }
        .schedule-done::after {
            content: '✓'; position: absolute; top: 10px; right: 10px;
            font-size: 24px; background: white; color: #667eea;
            width: 30px; height: 30px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
        }
        .log-section {
            background: white; border-radius: 15px; padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .log-title { font-size: 1.5em; color: #333; margin-bottom: 20px; font-weight: 600; }
        .log-container { max-height: 300px; overflow-y: auto; }
        .log-item {
            padding: 15px; border-left: 4px solid #667eea;
            background: #f8f9fa; margin-bottom: 10px; border-radius: 5px;
        }
        .log-time { font-weight: 600; color: #667eea; margin-bottom: 5px; }
        .log-message { color: #666; font-size: 0.95em; }
        .progress-bar {
            width: 100%; height: 10px; background: #e9ecef;
            border-radius: 5px; overflow: hidden; margin-top: 10px;
        }
        .progress-fill {
            height: 100%; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }
        @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.5;} }
        .pump-active { animation: pulse 1.5s ease-in-out infinite; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌱 Sistem Monitoring Irigasi Kangkung</h1>
            <p>Pemantauan Real-time & Kontrol Otomatis</p>
        </div>

        <div class="dashboard">
            <div class="card">
                <div class="card-header">
                    <div class="card-icon" style="background: #d4edda;">💧</div>
                    <div class="card-title">Kelembapan Tanah</div>
                </div>
                <div class="card-value" id="humidity">--</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="humidity-progress"></div>
                </div>
                <div style="margin-top: 10px;">
                    <span class="card-status" id="humidity-status">Memuat...</span>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-icon" style="background: #fff3cd;">☀️</div>
                    <div class="card-title">Intensitas Cahaya</div>
                </div>
                <div class="card-value" id="light">--</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="light-progress" style="background: linear-gradient(90deg, #ffc107 0%, #ff9800 100%);"></div>
                </div>
                <div style="margin-top: 10px;">
                    <span class="card-status" id="light-status">Memuat...</span>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-icon" style="background: #cce5ff;">⛅</div>
                    <div class="card-title">Kondisi Cuaca</div>
                </div>
                <div class="card-value" style="font-size: 1.8em;" id="weather">--</div>
                <div style="margin-top: 10px;">
                    <span class="card-status" id="weather-status">Memuat...</span>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-icon" style="background: #f8d7da;">⚙️</div>
                    <div class="card-title">Status Pompa</div>
                </div>
                <div class="card-value" style="font-size: 1.8em;" id="pump-status">MATI</div>
                <div style="margin-top: 10px;">
                    <span class="card-status status-warning" id="pump-badge">Standby</span>
                </div>
            </div>
        </div>

        <div class="irrigation-schedule">
            <div class="schedule-title">📅 Jadwal Penyiraman Hari Ini</div>
            <div class="schedule-grid">
                <div class="schedule-item" id="schedule-1">
                    <div class="schedule-time">06:00</div>
                    <div class="schedule-label">Penyiraman Pagi</div>
                </div>
                <div class="schedule-item" id="schedule-2">
                    <div class="schedule-time">12:00</div>
                    <div class="schedule-label">Penyiraman Siang</div>
                </div>
                <div class="schedule-item" id="schedule-3">
                    <div class="schedule-time">18:00</div>
                    <div class="schedule-label">Penyiraman Sore</div>
                </div>
            </div>
            <div style="margin-top: 20px; padding: 15px; background: #e7f3ff; border-radius: 10px; color: #004085;">
                <strong>ℹ️ Info:</strong> Sistem akan otomatis menyiram tambahan jika kelembapan tanah &lt; 40% atau cuaca sangat panas
            </div>
        </div>

        <div class="log-section">
            <div class="log-title">📋 Log Aktivitas</div>
            <div class="log-container" id="log-container"></div>
        </div>
    </div>

    <script>
        let logs = [];
        let scheduleStatus = [false, false, false];
        let extraWateringCount = 0;

        function addLog(message) {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('id-ID');
            logs.unshift({ time: timeStr, message: message });
            if (logs.length > 10) logs.pop();
            updateLogDisplay();
        }

        function updateLogDisplay() {
            const container = document.getElementById('log-container');
            container.innerHTML = logs.map(log => `
                <div class="log-item">
                    <div class="log-time">${log.time}</div>
                    <div class="log-message">${log.message}</div>
                </div>
            `).join('');
        }

        function getWeatherCondition(lightIntensity) {
            if (lightIntensity > 80) return { text: 'Cerah', emoji: '☀️', class: 'status-warning' };
            if (lightIntensity > 50) return { text: 'Berawan', emoji: '⛅', class: 'status-good' };
            return { text: 'Mendung', emoji: '☁️', class: 'status-good' };
        }

        function checkIrrigation(humidity, lightIntensity, isScheduled = false) {
            const hour = new Date().getHours();
            let shouldWater = false;
            let reason = '';
            if (isScheduled) {
                shouldWater = true;
                reason = 'Penyiraman terjadwal';
            } else if (humidity < 40) {
                shouldWater = true;
                reason = `Tanah kering (${humidity}%)`;
                extraWateringCount++;
            } else if (lightIntensity > 85 && humidity < 60) {
                shouldWater = true;
                reason = `Cuaca sangat panas (cahaya ${lightIntensity}%)`;
                extraWateringCount++;
            }

            if (shouldWater) activatePump(reason);
        }

        function activatePump(reason) {
            const pumpStatus = document.getElementById('pump-status');
            const pumpBadge = document.getElementById('pump-badge');
            pumpStatus.textContent = 'AKTIF';
            pumpBadge.textContent = 'Menyiram';
            pumpBadge.className = 'card-status status-active pump-active';
            addLog(`🚿 Pompa AKTIF - ${reason}`);
            setTimeout(() => {
                pumpStatus.textContent = 'MATI';
                pumpBadge.textContent = 'Standby';
                pumpBadge.className = 'card-status status-warning';
                addLog('✅ Penyiraman selesai');
            }, 30000);
        }

        function checkSchedule() {
            const now = new Date();
            const hour = now.getHours();
            const minute = now.getMinutes();
            if ((hour === 6 || hour === 12 || hour === 18) && minute === 0) {
                const idx = hour === 6 ? 0 : (hour === 12 ? 1 : 2);
                if (!scheduleStatus[idx]) {
                    scheduleStatus[idx] = true;
                    document.getElementById(`schedule-${idx + 1}`).classList.add('schedule-done');
                    checkIrrigation(getCurrentHumidity(), getCurrentLight(), true);
                }
            }
            if (hour === 0 && minute === 0) {
                scheduleStatus = [false, false, false];
                extraWateringCount = 0;
                for (let i = 1; i <= 3; i++) {
                    document.getElementById(`schedule-${i}`).classList.remove('schedule-done');
                }
            }
        }

        function getCurrentHumidity() {
            return parseInt(document.getElementById('humidity').textContent) || 0;
        }

        function getCurrentLight() {
            return parseInt(document.getElementById('light').textContent) || 0;
        }

        function updateSensors() {
            const humidity = Math.floor(Math.random() * 60) + 30;
            const lightIntensity = Math.floor(Math.random() * 100);

            document.getElementById('humidity').textContent = humidity + '%';
            document.getElementById('humidity-progress').style.width = humidity + '%';
            const hStatus = document.getElementById('humidity-status');
            if (humidity > 60) {
                hStatus.textContent = 'Optimal';
                hStatus.className = 'card-status status-good';
            } else if (humidity > 40) {
                hStatus.textContent = 'Normal';
                hStatus.className = 'card-status status-warning';
            } else {
                hStatus.textContent = 'Kering!';
                hStatus.className = 'card-status status-danger';
            }

            document.getElementById('light').textContent = lightIntensity + '%';
            document.getElementById('light-progress').style.width = lightIntensity + '%';
            const lStatus = document.getElementById('light-status');
            if (lightIntensity > 80) {
                lStatus.textContent = 'Sangat Terang';
                lStatus.className = 'card-status status-warning';
            } else if (lightIntensity > 50) {
                lStatus.textContent = 'Terang';
                lStatus.className = 'card-status status-good';
            } else {
                lStatus.textContent = 'Redup';
                lStatus.className = 'card-status status-good';
            }

            const weather = getWeatherCondition(lightIntensity);
            document.getElementById('weather').textContent = weather.emoji + ' ' + weather.text;
            document.getElementById('weather-status').textContent = weather.text;
            document.getElementById('weather-status').className = 'card-status ' + weather.class;

            checkIrrigation(humidity, lightIntensity, false);
        }

        addLog('✅ Sistem monitoring dimulai');
        updateSensors();
        setInterval(updateSensors, 5000);
        setInterval(checkSchedule, 60000);
        checkSchedule();
    </script>
</body>
</html>
