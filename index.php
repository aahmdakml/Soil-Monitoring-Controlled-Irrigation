<?php
session_start();
header('Content-Type: application/json');

// Inisialisasi data jika belum ada
if (!isset($_SESSION['logs'])) {
    $_SESSION['logs'] = [];
    $_SESSION['scheduleStatus'] = [false, false, false];
    $_SESSION['extraWateringCount'] = 0;
    $_SESSION['lastReset'] = date('Y-m-d');
    $_SESSION['pumpActive'] = false;
    $_SESSION['pumpActivatedAt'] = null;
}

// Reset di awal hari baru
if ($_SESSION['lastReset'] !== date('Y-m-d')) {
    $_SESSION['scheduleStatus'] = [false, false, false];
    $_SESSION['extraWateringCount'] = 0;
    $_SESSION['lastReset'] = date('Y-m-d');
}

// Fungsi untuk menambah log
function addLog($message) {
    $timeStr = date('H:i:s');
    array_unshift($_SESSION['logs'], [
        'time' => $timeStr,
        'message' => $message
    ]);
    
    if (count($_SESSION['logs']) > 10) {
        array_pop($_SESSION['logs']);
    }
}

// Fungsi untuk mendapatkan kondisi cuaca
function getWeatherCondition($lightIntensity) {
    if ($lightIntensity > 80) {
        return ['text' => 'Cerah', 'emoji' => '☀️', 'class' => 'status-warning'];
    } elseif ($lightIntensity > 50) {
        return ['text' => 'Berawan', 'emoji' => '⛅', 'class' => 'status-good'];
    } else {
        return ['text' => 'Mendung', 'emoji' => '☁️', 'class' => 'status-good'];
    }
}

// Fungsi untuk mengaktifkan pompa
function activatePump($reason) {
    $_SESSION['pumpActive'] = true;
    $_SESSION['pumpActivatedAt'] = time();
    addLog("🚿 Pompa AKTIF - $reason");
    
    // Simulasi penyiraman akan selesai dalam 30 detik
    // Akan dicek di checkPumpStatus()
}

// Fungsi untuk cek status pompa
function checkPumpStatus() {
    if ($_SESSION['pumpActive'] && $_SESSION['pumpActivatedAt']) {
        $elapsed = time() - $_SESSION['pumpActivatedAt'];
        if ($elapsed >= 30) {
            $_SESSION['pumpActive'] = false;
            $_SESSION['pumpActivatedAt'] = null;
            addLog('✅ Penyiraman selesai');
        }
    }
}

// Fungsi untuk cek irigasi
function checkIrrigation($humidity, $lightIntensity, $isScheduled = false) {
    $shouldWater = false;
    $reason = '';

    if ($isScheduled) {
        $shouldWater = true;
        $reason = 'Penyiraman terjadwal';
    } elseif ($humidity < 40) {
        $shouldWater = true;
        $reason = "Tanah kering ({$humidity}%)";
        $_SESSION['extraWateringCount']++;
    } elseif ($lightIntensity > 85 && $humidity < 60) {
        $shouldWater = true;
        $reason = "Cuaca sangat panas (cahaya {$lightIntensity}%)";
        $_SESSION['extraWateringCount']++;
    }

    if ($shouldWater && !$_SESSION['pumpActive']) {
        activatePump($reason);
    }
}

// Handle request berdasarkan action
$action = $_GET['action'] ?? '';

switch ($action) {
    case 'getSensors':
        // Simulasi pembacaan sensor
        $humidity = rand(30, 90);
        $lightIntensity = rand(0, 100);
        
        // Cek status pompa
        checkPumpStatus();
        
        // Status kelembapan
        if ($humidity > 60) {
            $humidityStatus = ['text' => 'Optimal', 'class' => 'status-good'];
        } elseif ($humidity > 40) {
            $humidityStatus = ['text' => 'Normal', 'class' => 'status-warning'];
        } else {
            $humidityStatus = ['text' => 'Kering!', 'class' => 'status-danger'];
        }
        
        // Status cahaya
        if ($lightIntensity > 80) {
            $lightStatus = ['text' => 'Sangat Terang', 'class' => 'status-warning'];
        } elseif ($lightIntensity > 50) {
            $lightStatus = ['text' => 'Terang', 'class' => 'status-good'];
        } else {
            $lightStatus = ['text' => 'Redup', 'class' => 'status-good'];
        }
        
        // Kondisi cuaca
        $weather = getWeatherCondition($lightIntensity);
        
        // Status pompa
        $pumpStatus = $_SESSION['pumpActive'] ? 'AKTIF' : 'MATI';
        $pumpBadge = $_SESSION['pumpActive'] 
            ? ['text' => 'Menyiram', 'class' => 'status-active pump-active']
            : ['text' => 'Standby', 'class' => 'status-warning'];
        
        // Cek apakah perlu penyiraman tambahan
        checkIrrigation($humidity, $lightIntensity, false);
        
        echo json_encode([
            'humidity' => $humidity,
            'humidityStatus' => $humidityStatus,
            'light' => $lightIntensity,
            'lightStatus' => $lightStatus,
            'weather' => $weather,
            'pumpStatus' => $pumpStatus,
            'pumpBadge' => $pumpBadge,
            'logs' => $_SESSION['logs']
        ]);
        break;
        
    case 'checkSchedule':
        $hour = (int)date('H');
        $minute = (int)date('i');
        
        // Cek jadwal 06:00, 12:00, 18:00
        if (($hour === 6 || $hour === 12 || $hour === 18) && $minute === 0) {
            $scheduleIndex = $hour === 6 ? 0 : ($hour === 12 ? 1 : 2);
            
            if (!$_SESSION['scheduleStatus'][$scheduleIndex]) {
                $_SESSION['scheduleStatus'][$scheduleIndex] = true;
                
                // Simulasi pembacaan sensor untuk penyiraman terjadwal
                $humidity = rand(30, 90);
                $lightIntensity = rand(0, 100);
                
                checkIrrigation($humidity, $lightIntensity, true);
            }
        }
        
        echo json_encode([
            'scheduleStatus' => $_SESSION['scheduleStatus'],
            'extraWateringCount' => $_SESSION['extraWateringCount']
        ]);
        break;
        
    case 'getLogs':
        echo json_encode([
            'logs' => $_SESSION['logs']
        ]);
        break;
        
    case 'resetSystem':
        $_SESSION['logs'] = [];
        $_SESSION['scheduleStatus'] = [false, false, false];
        $_SESSION['extraWateringCount'] = 0;
        $_SESSION['pumpActive'] = false;
        $_SESSION['pumpActivatedAt'] = null;
        addLog('✅ Sistem monitoring dimulai');
        
        echo json_encode([
            'success' => true,
            'message' => 'Sistem berhasil direset'
        ]);
        break;
        
    default:
        echo json_encode([
            'error' => 'Invalid action'
        ]);
        break;
}
?>