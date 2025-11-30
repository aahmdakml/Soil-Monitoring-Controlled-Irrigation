import time
import random
import requests

# ===================== CONFIG =====================

API_BASE = "http://localhost:8000"   # ganti ke IP laptop kalau perlu
DEVICE_ID = "raspi-1"

NUM_POINTS = 40          # berapa banyak titik sensor
INTERVAL_SEC = 0.1       # jeda antar titik (detik)

# kalau mau sekalian test logs aktuator:
SIMULATE_ACTUATORS = True


# ===================== API HELPERS =====================

def post_json(path: str, payload: dict, timeout: float = 3.0):
    url = API_BASE + path
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json() if r.content else {}
    except Exception as e:
        print(f"[POST {path}] FAIL:", e)
        return None


# --------- SENSOR & EVENTS (EDGE API) ---------

def send_sensor(t, h, light, soil):
    payload = {
        "device_id": DEVICE_ID,
        "temperature": float(t),
        "humidity": float(h),
        "light": float(light),
        "soil_moisture": float(soil),
    }
    res = post_json("/api/edge/sensor", payload)
    if res is not None:
        print("[SENSOR] OK:", payload)
    else:
        print("[SENSOR] FAIL:", payload)


def send_event(pump_status=None, servo_position=None, source="edge", message="", command_id=None):
    payload = {
        "device_id": DEVICE_ID,
        "pump_status": pump_status,
        "servo_position": servo_position,
        "source": source,
        "message": message,
        "command_id": command_id,
    }
    res = post_json("/api/edge/event", payload)
    if res is not None:
        print("[EVENT] OK:", payload)
    else:
        print("[EVENT] FAIL:", payload)


# --------- COMMANDS (UI API) ---------

def queue_pump_command(status: str):
    """Simulasi user klik tombol Pump ON/OFF di FE."""
    payload = {"status": status}
    res = post_json("/api/pump", payload)
    if res is not None:
        print(f"[CMD] Pump {status} queued:", res)
    else:
        print(f"[CMD] Pump {status} FAILED")


def queue_servo_command(position: str):
    """Simulasi user klik tombol Servo Open/Half/Close di FE."""
    payload = {"position": position}
    res = post_json("/api/servo", payload)
    if res is not None:
        print(f"[CMD] Servo {position} queued:", res)
    else:
        print(f"[CMD] Servo {position} FAILED")


# ===================== MAIN =====================

def main():
    print(f"Sending {NUM_POINTS} dummy sensor points to {API_BASE} ...")

    # Base nilai kira-kira realistis
    base_temp = 30.0      # °C
    base_hum = 60.0       # %
    base_light = 300      # ADC
    base_soil = 400       # ADC

    for i in range(NUM_POINTS):
        # bikin variasi random kecil
        t = base_temp + random.uniform(-2.5, 2.5)
        h = base_hum + random.uniform(-5, 5)
        light = base_light + random.randint(-80, 80)
        soil = base_soil + random.randint(-60, 60)

        send_sensor(t, h, light, soil)

        # Sekalian test logs aktuator sedikit
        if SIMULATE_ACTUATORS:
            # di beberapa titik, kirim event langsung (seolah edge nulis log)
            if i in (5, 15, 25):
                send_event(
                    pump_status="on" if i == 5 else "off",
                    servo_position=None,
                    source="edge",
                    message=f"Dummy pump event at i={i}"
                )
            if i in (10, 20, 30):
                pos = "open" if i == 10 else "half" if i == 20 else "close"
                send_event(
                    pump_status=None,
                    servo_position=pos,
                    source="edge",
                    message=f"Dummy servo event at i={i}"
                )

            # dan sekali-kali simulasi user queue command via UI API
            if i == 3:
                queue_pump_command("on")
            if i == 8:
                queue_pump_command("off")
            if i == 12:
                queue_servo_command("open")
            if i == 18:
                queue_servo_command("half")
            if i == 28:
                queue_servo_command("close")

        time.sleep(INTERVAL_SEC)

    print("Done sending dummy data.")


if __name__ == "__main__":
    main()
