# services/gpio_service.py
from typing import Tuple
from ..config import PUMP_GPIO, SERVO_GPIO
from .event_service import log_event

# Biar bisa develop di PC tanpa RPi.GPIO
try:
    import RPi.GPIO as GPIO
    _HAS_GPIO = True
except ImportError:
    GPIO = None
    _HAS_GPIO = False

current_pump_status = "off"
current_servo_pos = "close"

def setup_gpio():
    if not _HAS_GPIO:
        print("[WARN] RPi.GPIO not available, running in dummy mode.")
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PUMP_GPIO, GPIO.OUT)
    GPIO.output(PUMP_GPIO, GPIO.LOW)

    GPIO.setup(SERVO_GPIO, GPIO.OUT)
    global _servo_pwm
    _servo_pwm = GPIO.PWM(SERVO_GPIO, 50)  # 50 Hz
    _servo_pwm.start(0)

def cleanup_gpio():
    if not _HAS_GPIO:
        return
    GPIO.cleanup()

def _set_servo_angle(angle: float):
    if not _HAS_GPIO:
        print(f"[SERVO] Dummy angle: {angle}")
        return

    duty = 2 + (angle / 18.0)  # kira-kira mapping 0-180
    GPIO.output(SERVO_GPIO, True)
    _servo_pwm.ChangeDutyCycle(duty)
    import time
    time.sleep(0.5)
    GPIO.output(SERVO_GPIO, False)
    _servo_pwm.ChangeDutyCycle(0)

def set_pump(status: str, source: str = "system"):
    global current_pump_status
    status = status.lower()
    if status not in ["on", "off"]:
        raise ValueError("status must be 'on' or 'off'")

    if _HAS_GPIO:
        import RPi.GPIO as GPIO_local  # alias
        GPIO_local.output(PUMP_GPIO, GPIO_local.HIGH if status == "on" else GPIO_local.LOW)
    else:
        print(f"[PUMP] Dummy set: {status}")

    current_pump_status = status
    log_event(pump_status=status, source=source, message=f"Pump set {status}")

def set_servo_position(position: str, source: str = "system"):
    global current_servo_pos
    pos = position.lower()
    if pos == "open":
        _set_servo_angle(90)
    elif pos == "half":
        _set_servo_angle(45)
    elif pos == "close":
        _set_servo_angle(0)
    else:
        raise ValueError("position must be 'open', 'half', or 'close'")

    current_servo_pos = pos
    log_event(servo_position=pos, source=source, message=f"Servo {pos}")

def get_actuator_status() -> Tuple[str, str]:
    return current_pump_status, current_servo_pos
