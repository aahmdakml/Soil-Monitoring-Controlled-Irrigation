# smart_plant_gateway_web_client.py - RPi Gateway Integrated with Custom Web Server Communication
# Date: 2025-12-10
# Version: Final with Schedule Robustness Check

import time, json, signal, sys
from typing import Optional, List, Dict, Any
import serial
import requests
import joblib 
import datetime
import numpy as np 

# Ensure RPi.GPIO is installed and running (RPi only)
try:
    import RPi.GPIO as GPIO 
    if sys.platform != 'linux':
        print("[WARN] Not a Linux/RPi system. GPIO will be disabled.")
        GPIO = None
except Exception:
    print("[ERROR] Failed to import RPi.GPIO. RPi actuators will not function.")
    GPIO = None 

# ======================= WEB SERVER & TIMING CONFIGURATION =======================
DEVICE_ID = "raspi-1"
# >>> GANTI DENGAN ALAMAT IP DAN PORT WEB SERVER ANDA <<<
SERVER_BASE = "http://10.3.74.50:8000" 

# Intervals (in seconds)
PUBLISH_INTERVAL_SECONDS = 15.0 # Interval mengirim data sensor ke server
COMMAND_INTERVAL_SECONDS = 5.0  # Interval polling perintah umum (/api/edge/commands)
SCHEDULE_INTERVAL_SECONDS = 60.0 # Interval polling jadwal khusus (/api/schedule)
REMOTE_TIMEOUT_SECONDS = 30.0 # Waktu timeout untuk Remote Control sebelum kembali ke LOCAL

# ======================= SERIAL & SENSOR CONFIGURATION =======================
SERIAL_PORT = "/dev/serial0" 
BAUD_RATE = 115200

# Thresholds (digunakan jika model ML gagal dimuat)
SOIL_THRESHOLD = 1800 
HUM_MAX = 70 
LIGHT_MIN = 300 

# ======================= ML MODEL CONFIGURATION =======================
ML_MODEL_FILENAME = "smart_watering_model.pkl"
SMART_PLANT_MODEL = None

try:
    # Memuat model ML (Pastikan file ini ada di direktori yang sama)
    SMART_PLANT_MODEL = joblib.load(ML_MODEL_FILENAME)
    print(f"[ML-INFO] Successfully loaded ML model: {ML_MODEL_FILENAME}")
except Exception as e:
    print(f"[ML-ERROR] Failed to load ML model '{ML_MODEL_FILENAME}'. Error: {e}")
    print("[ML-WARN] Local decision logic will use the original threshold rules.")


# ======================= GPIO CONFIG (Actuators on RPi) =======================
SERVO_PWM: Optional[GPIO.PWM] = None
current_servo_dc = 0.0 
RELAY_PIN = 13 
SERVO_PIN = 12 
# Duty Cycle untuk Servo 
DUTY_CYCLE_OFF = 1.5 
DUTY_CYCLE_HALF_ON = 3.4 
DUTY_CYCLE_ON = 6.8 
SMOOTH_STEPS = 50 
SMOOTH_DELAY = 0.005 

if GPIO:
    GPIO.setmode(GPIO.BCM) 
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    SERVO_PWM = GPIO.PWM(SERVO_PIN, 50)
    SERVO_PWM.start(0) 
    GPIO.output(RELAY_PIN, GPIO.LOW) 
    SERVO_PWM.ChangeDutyCycle(DUTY_CYCLE_OFF)
    current_servo_dc = DUTY_CYCLE_OFF
    time.sleep(0.5) 
    print(f"[GPIO] RPi Actuators Ready.")


# ======================= STATE & BUFFERS =======================
running = True
ser: Optional[serial.Serial] = None
serial_buffer = ""
has_valid_data = False 
latest_data: Dict[str, str] = {} 
latest_decision = "WATER_OFF" 
current_control_mode = "LOCAL" 
last_remote_command_time = 0.0 
WATERING_SCHEDULE: List[Dict[str, Any]] = []
is_scheduled_watering = False
scheduled_watering_end_time = 0.0


# ---------- Utility Functions ----------
def safe_str(v) -> str:
    """Membersihkan dan mengkonversi nilai ke string numerik yang aman."""
    try:
        s = str(v).strip()
        if s.lower() in ("", "nan", "none", "-1.0", "none"): 
            return "0"
        return str(float(s))
    except Exception: 
        return "0"

def handle_sigint(sig, frame):
    """Cleanup saat program dihentikan."""
    global running, GPIO, SERVO_PWM, RELAY_PIN
    print("\n[INFO] Exiting upon user request...")
    if GPIO:
        if SERVO_PWM:
            try: SERVO_PWM.ChangeDutyCycle(DUTY_CYCLE_OFF); time.sleep(0.1); SERVO_PWM.stop()
            except Exception: pass
        try: GPIO.output(RELAY_PIN, GPIO.LOW) 
        except Exception: pass
        GPIO.cleanup()
        print("[INFO] GPIO cleaned up.")
    global ser
    try:
        if ser and ser.is_open: ser.close()
    except Exception: pass
    running = False
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

def open_serial():
    global ser, serial_buffer
    if ser and getattr(ser, "is_open", False): return True
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1) 
        time.sleep(1.0)
        ser.flushInput(); ser.flushOutput(); serial_buffer = "" 
        print(f"[INFO] Serial opened: {SERIAL_PORT} @ {BAUD_RATE}")
        return True
    except Exception as e:
        ser = None
        print(f"[ERROR] Failed to open serial: {e}")
        return False

def close_serial():
    global ser
    try:
        if ser and ser.is_open: ser.close()
    except Exception: pass

def send_event(pump_status=None, servo_position=None, source="edge", message="", command_id=None):
    """Mengirim event atau laporan status kembali ke server."""
    payload = {
        "device_id": DEVICE_ID, "pump_status": pump_status, "servo_position": servo_position,
        "source": source, "message": message, "command_id": command_id,
    }
    url = f"{SERVER_BASE}/api/edge/event"
    try: 
        requests.post(url, json=payload, timeout=3).raise_for_status()
        if command_id:
            print(f"[EVENT] Status report sent successfully (CMD ID: {command_id})")
    except Exception as e: 
        print(f"[EVENT] Failed to send status report ({url}): {e}")

# ======================= ACTUATOR CONTROL & LOGIC =======================

def decide_watering(data: dict) -> str:
    """Mengambil keputusan penyiraman berdasarkan ML atau aturan."""
    global SMART_PLANT_MODEL
    try:
        # Mengambil data sensor
        soil, temp, hum, light = (float(safe_str(data.get(k, 0))) for k in ["soil", "temp", "hum", "light"])
    except Exception: 
        return "WATER_OFF" 
        
    # 1. Logika ML Model
    if SMART_PLANT_MODEL is not None:
        try:
            current_hour = datetime.datetime.now().hour
            features = [temp, hum, light, soil, current_hour]
            prediction = SMART_PLANT_MODEL.predict(np.array(features).reshape(1, -1))[0]
            decision = "WATER_ON" if prediction == 1 or str(prediction).upper() in ["WATER_ON", "1.0", "TRUE"] else "WATER_OFF"
            print(f"[DEBUG-LOGIC] ML Model Decision: {decision}")
            return decision
        except Exception: 
            print("[ML-ERROR] Error during ML prediction. Falling back to Rule-Based Logic.")
            
    # 2. Rule-Based Fallback Logic
    is_soil_dry = soil > SOIL_THRESHOLD
    is_air_dry = hum < HUM_MAX
    is_light_sufficient = light > LIGHT_MIN
    
    decision = "WATER_ON" if is_soil_dry and is_air_dry and is_light_sufficient else "WATER_OFF"
    print(f"[DEBUG-LOGIC] Rule-Based Fallback Decision: {decision}")
    return decision


def move_servo_smoothly(target_dc: float):
    """Menggerakkan servo secara bertahap."""
    global SERVO_PWM, current_servo_dc, SMOOTH_STEPS, SMOOTH_DELAY, GPIO
    if not GPIO or SERVO_PWM is None:
        current_servo_dc = target_dc; return
    if abs(target_dc - current_servo_dc) < 0.1: 
        SERVO_PWM.ChangeDutyCycle(target_dc); current_servo_dc = target_dc; return
    
    start_dc = current_servo_dc
    step = (target_dc - start_dc) / SMOOTH_STEPS
    
    for i in range(1, SMOOTH_STEPS + 1):
        if not running: break 
        new_dc = start_dc + step * i
        new_dc = max(DUTY_CYCLE_OFF, min(DUTY_CYCLE_ON, new_dc))
        SERVO_PWM.ChangeDutyCycle(new_dc)
        time.sleep(SMOOTH_DELAY) 
        
    if running:
        SERVO_PWM.ChangeDutyCycle(target_dc)
        current_servo_dc = target_dc
        # print(f"[SERVO] Moved to {target_dc:.2f}% DC.")

def set_pump_state(state: str):
    """Mengontrol relay pompa."""
    global GPIO, RELAY_PIN
    state = state.lower()
    if not GPIO: return
    if state == "on": 
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        print("[ACTION] Pump: ON (HIGH)")
    elif state == "off": 
        GPIO.output(RELAY_PIN, GPIO.LOW)
        print("[ACTION] Pump: OFF (LOW)")

def set_servo_position(position: str):
    """Mengontrol posisi servo (katup air)."""
    global DUTY_CYCLE_ON, DUTY_CYCLE_OFF, DUTY_CYCLE_HALF_ON
    position = position.lower()
    if position == "open": move_servo_smoothly(DUTY_CYCLE_ON)
    elif position == "half_open": move_servo_smoothly(DUTY_CYCLE_HALF_ON)
    elif position == "close": move_servo_smoothly(DUTY_CYCLE_OFF)
    else: print(f"[WARN] Invalid servo position: {position}")

def check_schedule_watering():
    """Mengimplementasikan Prioritas 2 (SCHEDULE) dan Prioritas 3 (LOCAL/AUTO)."""
    global WATERING_SCHEDULE, is_scheduled_watering, scheduled_watering_end_time, latest_decision, latest_data
    now = time.time()
    current_dt = datetime.datetime.now()
    current_time_str = current_dt.strftime("%H:%M") 
    current_date_str = current_dt.strftime("%Y-%m-%d") 
    
    # --- 1. Prioritas 2: Eksekusi Jadwal Aktif ---
    if is_scheduled_watering:
        if now < scheduled_watering_end_time:
            # Tetap dalam mode terjadwal
            if latest_decision != "SCHEDULE_ON": latest_decision = "SCHEDULE_ON"
            return
        else:
            # Jadwal selesai, matikan aktuator dan perbarui status eksekusi
            print("[SCHEDULE-END] Scheduled watering finished. Turning OFF actuators.")
            set_pump_state("off"); set_servo_position("close")
            is_scheduled_watering = False
            # Tandai jadwal yang baru saja selesai agar tidak dieksekusi lagi hari ini
            for item in WATERING_SCHEDULE:
                if item["time"] == current_time_str or \
                   item["time"] == (current_dt - datetime.timedelta(minutes=1)).strftime("%H:%M"):
                    item["last_executed_date"] = current_date_str; break 
    
    # --- 2. Prioritas 2: Mulai Jadwal Baru ---
    if not is_scheduled_watering:
        for item in WATERING_SCHEDULE:
            if current_time_str == item["time"] and item["last_executed_date"] != current_date_str:
                duration = item.get("duration_sec", 10) 
                print(f"\n[SCHEDULE-START] Starting scheduled watering for {duration} seconds at {current_time_str}.")
                set_servo_position("open"); set_pump_state("on")
                is_scheduled_watering = True
                scheduled_watering_end_time = now + duration
                latest_decision = "SCHEDULE_ON"
                return # JANGAN PERGI KE LOGIKA ML/SENSOR
    
    # --- 3. Prioritas 3: LOCAL/AUTO (ML/Rule-Based) ---
    current_decision = decide_watering(latest_data)
    latest_decision = current_decision 
    if current_decision == "WATER_ON":
        set_servo_position("open"); set_pump_state("on")
    else:
        set_pump_state("off"); set_servo_position("close")
    return

# ======================= WEB SERVER COMMUNICATION FUNCTIONS =======================

def send_sensor_data_to_web(data: dict, decision: str) -> bool:
    """Mengirim data sensor ke /api/edge/sensor."""
    servo_pos_str = "CLOSE"
    if abs(current_servo_dc - DUTY_CYCLE_ON) < 0.1: servo_pos_str = "OPEN"
    elif abs(current_servo_dc - DUTY_CYCLE_HALF_ON) < 0.1: servo_pos_str = "HALF_OPEN"
        
    try:
        payload = {
            "device_id": DEVICE_ID, "temperature": float(safe_str(data.get('temp'))), 
            "humidity": float(safe_str(data.get('hum'))), "light": float(safe_str(data.get('light'))), 
            "soil_moisture": float(safe_str(data.get('soil'))), "auto_decision": decision.upper(), 
            "pump_status": "ON" if GPIO and GPIO.input(RELAY_PIN) == GPIO.HIGH else "OFF",
            "servo_position": servo_pos_str, "control_mode": current_control_mode 
        }
    except ValueError: return False
    url = f"{SERVER_BASE}/api/edge/sensor"
    try:
        requests.post(url, json=payload, timeout=5).raise_for_status() 
        return True
    except requests.exceptions.RequestException as e:
        print(f"[WEB-ERROR] Failed to send data to server ({url}): {e}")
        return False

def fetch_and_execute_commands():
    """Mengambil dan mengeksekusi perintah umum (Prioritas 1) dari /api/edge/commands."""
    global current_control_mode, last_remote_command_time
    url = f"{SERVER_BASE}/api/edge/commands" 
    
    try:
        response = requests.get(url, params={"device_id": DEVICE_ID}, timeout=3)
        response.raise_for_status()
        cmds = response.json()
        if not cmds: return
        
        last_remote_command_time = time.time()
        print(f"[CMD] Received {len(cmds)} new general commands.")
        
        for cmd in cmds:
            cmd_id = cmd.get("id", "N/A"); ctype = cmd.get("type"); payload = cmd.get("payload", {}) or {}
            
            if ctype in ["pump", "servo"]:
                current_control_mode = "REMOTE" # Prioritas 1
                if ctype == "pump": set_pump_state(payload.get("status", "off"))
                elif ctype == "servo": set_servo_position(payload.get("position", "close"))
            elif ctype == "mode":
                new_mode = payload.get("status", "unknown").upper()
                if new_mode in ["AUTO", "LOCAL"]: current_control_mode = "LOCAL"
                elif new_mode == "REMOTE": current_control_mode = "REMOTE"
            
            send_event(
                source="edge",
                message=f"Command {cmd_id} ({ctype}) executed. New mode: {current_control_mode}",
                command_id=cmd_id,
            )

    except requests.exceptions.RequestException as e:
        print(f"[WEB-ERROR] Failed to fetch general commands from server ({url}): {e}")
    except json.JSONDecodeError:
        print("[WEB-ERROR] Command response is not valid JSON.")
        
def fetch_and_update_schedule():
    """
    Mengambil jadwal penyiraman langsung dari endpoint /api/schedule.
    Ini adalah fungsi yang telah direvisi untuk menangani DICT atau LIST respons.
    """
    global WATERING_SCHEDULE, current_control_mode
    
    if current_control_mode == "REMOTE":
        print("[SCHED-FETCH] Schedule fetch ignored. Must be in LOCAL/AUTO mode.")
        return

    SCHEDULE_URL = f"{SERVER_BASE}/api/schedule"
    
    try:
        response = requests.get(SCHEDULE_URL, params={"device_id": DEVICE_ID}, timeout=3)
        response.raise_for_status()
        
        raw_data = response.json()
        print(f"[DEBUG-PAYLOAD] Raw schedule list received from /api/schedule: {raw_data}")

        schedule_items_to_process: List[Dict[str, Any]] = []

        # --- LOGIKA PENANGANAN STRUKTUR RESPON WEB SERVER ---
        if isinstance(raw_data, dict):
            # Skenario 1: Web Server mengirimkan satu objek (DICT)
            print("[INFO-PARSING] Parsing single schedule object (dict).")
            # Hanya proses jika 'enabled' True atau jika kunci 'enabled' tidak ada.
            if raw_data.get('enabled', True) in [True, "true", "TRUE"]:
                # Mapping kunci Web Server ke kunci internal RPi
                item = {
                    "time": raw_data.get('time_hhmm'), 
                    "duration_sec": raw_data.get('duration_seconds')
                }
                schedule_items_to_process.append(item)
            else:
                 print("[INFO] Single schedule received but is explicitly disabled.")
                 WATERING_SCHEDULE = [] # Kosongkan jadwal jika dimatikan
                 return
                 
        elif isinstance(raw_data, list):
            # Skenario 2: Web Server mengirim daftar/array (LIST) dari banyak jadwal
            print("[INFO-PARSING] Parsing multiple schedule objects (list).")
            schedule_items_to_process = raw_data
        else:
            print(f"[ERROR-VALIDATION] Schedule fetch rejected. Expected a dict or a list, got {type(raw_data)}.")
            return
        # --------------------------------------------------
        
        valid_schedule: List[Dict[str, Any]] = []
        for item in schedule_items_to_process:
            # Validasi kunci tugas RPi internal (time dan duration_sec)
            if "time" in item and "duration_sec" in item:
                try:
                    datetime.datetime.strptime(item["time"], "%H:%M")
                    item["duration_sec"] = int(item["duration_sec"])
                    item["last_executed_date"] = item.get("last_executed_date", "") # Pertahankan status eksekusi jika ada, jika tidak, reset.
                    valid_schedule.append(item)
                except ValueError as e:
                    print(f"[WARN] Invalid time format or duration in schedule item: {item}. Error: {e}")
            else:
                print(f"[WARN] Schedule item rejected. Missing internal keys 'time' or 'duration_sec': {item}")

        if valid_schedule:
            # Hanya perbarui jika jadwal berubah
            if str(valid_schedule) != str(WATERING_SCHEDULE):
                WATERING_SCHEDULE = valid_schedule
                print(f"\n[ACTION-WEB] SUCCESSFULLY RECEIVED NEW SCHEDULE from /api/schedule: {len(WATERING_SCHEDULE)} task(s) updated.")
        else:
            if WATERING_SCHEDULE:
                 print("[WARN] Received schedule data is empty or invalid. Keeping current schedule.")
            else:
                 print("[INFO] No valid schedule received yet. WATERING_SCHEDULE remains empty.")

    except requests.exceptions.RequestException as e:
        print(f"[WEB-ERROR] Failed to fetch schedule from server ({SCHEDULE_URL}): {e}")
    except json.JSONDecodeError:
        print(f"[WEB-ERROR] Schedule response from {SCHEDULE_URL} is not valid JSON.")


# ======================= MAIN LOOP =======================
def main():
    global running, ser, serial_buffer, has_valid_data, latest_data, latest_decision, current_control_mode, last_remote_command_time
    
    print(f"[INFO] Starting RPi Gateway Web Client. ID: {DEVICE_ID}")
    
    last_remote_command_time = time.time() 
    open_serial()
    
    # Inisialisasi timer agar langsung berjalan pada loop pertama
    last_publish_time = time.time() - PUBLISH_INTERVAL_SECONDS 
    last_command_time = time.time() - COMMAND_INTERVAL_SECONDS
    last_schedule_fetch_time = time.time() - SCHEDULE_INTERVAL_SECONDS 

    while running:
        now = time.time()
        
        # --- 0. Remote Control Timeout Check --- 
        if current_control_mode == "REMOTE":
            if now - last_remote_command_time >= REMOTE_TIMEOUT_SECONDS:
                print(f"\n[TIMEOUT] Remote Control timeout. Returning to LOCAL.")
                current_control_mode = "LOCAL"
                # Matikan aktuator saat kembali ke mode otomatis
                set_pump_state("off"); set_servo_position("close")
                send_event(source="edge", message="Remote control timed out. Switching back to LOCAL/AUTO mode.")

        # --- 1. Read Serial from ESP32 & Instant Decision ---
        if ser and getattr(ser, "is_open", False):
            try:
                if ser.in_waiting > 0:
                    raw_bytes = ser.read(ser.in_waiting); serial_buffer += raw_bytes.decode(errors="ignore")
                
                # Parsing pesan yang valid (antara START dan END)
                while "START" in serial_buffer and "END" in serial_buffer:
                    start_index = serial_buffer.find("START"); end_index = serial_buffer.find("END", start_index)
                    if start_index != -1 and end_index != -1:
                        full_message = serial_buffer[start_index : end_index + 3]; serial_buffer = serial_buffer[end_index + 3:]
                        json_start = full_message.find('{', start_index); json_end = full_message.rfind('}', json_start)
                        if json_start != -1 and json_end != -1:
                            try:
                                data = json.loads(full_message[json_start:json_end+1])
                                latest_data["temp"] = safe_str(data.get("temp")); latest_data["hum"] = safe_str(data.get("hum")); 
                                latest_data["light"] = safe_str(data.get("light")); latest_data["soil"] = safe_str(data.get("soil"))
                                has_valid_data = True
                                
                                print(f"\n[SENSOR READ] New data received: {latest_data}")
                                
                                # Logika Prioritas 2 & 3 (Schedule/Auto)
                                if current_control_mode == "LOCAL": 
                                    check_schedule_watering() 
                                else:
                                    print(f"[OVERRIDE] Local Auto/Schedule control ignored because Control Mode: {current_control_mode}")

                            except json.JSONDecodeError: 
                                print("[WARN] Failed to parse JSON from serial.")
                        
                    else: break 
            except Exception as e: 
                print(f"[ERROR] Serial read error: {e}")
                close_serial(); time.sleep(2)
        else: open_serial(); time.sleep(1)

        # --- 2. Publish Sensor Cycle to Web Server ---
        if has_valid_data and now - last_publish_time >= PUBLISH_INTERVAL_SECONDS:
            print(f"\n--- PUBLISH SENSOR CYCLE TO WEB ({PUBLISH_INTERVAL_SECONDS}s) ---")
            send_sensor_data_to_web(latest_data, latest_decision)
            last_publish_time = now 

        # --- 3. Fetch & Execute Remote Command Cycle (General Commands) ---
        if now - last_command_time >= COMMAND_INTERVAL_SECONDS:
            fetch_and_execute_commands()
            last_command_time = now
            
        # --- 4. Fetch & Update Schedule Cycle (Dedicated Schedule Endpoint) ---
        if now - last_schedule_fetch_time >= SCHEDULE_INTERVAL_SECONDS:
            print(f"\n--- FETCH SCHEDULE CYCLE FROM /api/schedule ({SCHEDULE_INTERVAL_SECONDS}s) ---")
            fetch_and_update_schedule()
            last_schedule_fetch_time = now
            
        time.sleep(0.01)

if _name_ == "_main_":
    try:
        main()
    except KeyboardInterrupt:
        handle_sigint(None, None)