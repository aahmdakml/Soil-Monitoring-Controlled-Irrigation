# 🌱 Soil Monitoring & Controlled Irrigation System

An intelligent IoT-based irrigation system that uses machine learning and sensor data to automatically control plant watering.   The system features a Raspberry Pi gateway that communicates with ESP32 sensors and a web server for remote monitoring and control.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)

## 📋 Table of Contents
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Hardware Requirements](#-hardware-requirements)
- [Software Requirements](#-software-requirements)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Control Modes](#-control-modes)
- [API Endpoints](#-api-endpoints)
- [ML Model](#-ml-model)
- [Dataset](#-dataset)
- [Troubleshooting](#-troubleshooting)

## ✨ Features

### 🤖 Smart Automation
- **Machine Learning Integration**: Uses trained ML model (`smart_watering_model.pkl`) for intelligent watering decisions
- **Rule-Based Fallback**:  Automatic threshold-based logic if ML model is unavailable
- **Multi-Priority Control System**:
  - **Priority 1**: Remote Control (manual override via web)
  - **Priority 2**:  Schedule-based watering
  - **Priority 3**: Local AUTO mode (ML/sensor-based)

### 📊 Real-time Monitoring
- Temperature, humidity, light, and soil moisture sensors
- Live data transmission to web server every 15 seconds
- Sensor data visualization through web dashboard

### 🎛️ Flexible Control
- **LOCAL Mode**:  Autonomous ML/rule-based decisions
- **REMOTE Mode**: Manual control via web interface
- **Scheduled Watering**: Time-based irrigation schedules
- Smooth servo motor control for gradual valve operation
- Relay-controlled water pump

### 🌐 Web Integration
- RESTful API communication with custom web server
- Remote command execution
- Real-time status updates
- Schedule management via web interface

## 🏗️ System Architecture

```
┌─────────────┐      Serial       ┌──────────────┐      HTTP/REST      ┌─────────────┐
│   ESP32     │ ═════════════════► │ Raspberry Pi │ ◄═══════════════════► │ Web Server  │
│  (Sensors)  │   (115200 baud)    │  (Gateway)   │   (WiFi/Ethernet)   │  (Backend)  │
└─────────────┘                    └──────────────┘                     └─────────────┘
      │                                   │                                     │
      │                                   │                                     │
   ┌──▼──┐                           ┌────▼────┐                          ┌────▼────┐
   │ DHT │                           │ Relay   │                          │ Frontend│
   │Light│                           │ Servo   │                          │   UI    │
   │Soil │                           │ Pump    │                          └─────────┘
   └─────┘                           └─────────┘
```

### Communication Flow
1. **ESP32** reads sensors → sends JSON data via serial to RPi
2. **Raspberry Pi** processes data → makes watering decisions
3. **RPi** controls actuators (pump/servo) based on priority logic
4. **RPi** sends sensor data and status to web server
5. **Web Server** provides UI for monitoring and remote control

## 🔧 Hardware Requirements

### Core Components
- **Raspberry Pi** (3B+/4 recommended)
  - GPIO pins for actuator control
  - Serial port enabled (`/dev/serial0`)
- **ESP32 Development Board**
  - DHT temperature/humidity sensor
  - Photoresistor (light sensor)
  - Soil moisture sensor
- **Actuators**
  - 5V Relay module (for pump control)
  - Servo motor (for valve control)
  - Water pump (12V recommended)

### Wiring Diagram
| Component | GPIO Pin | Description |
|-----------|----------|-------------|
| Relay     | GPIO 13  | Water pump control |
| Servo     | GPIO 12  | Valve position control (PWM) |
| ESP32 TX  | RX       | Serial communication |
| ESP32 RX  | TX       | Serial communication |

## 💻 Software Requirements

### Raspberry Pi
```
- Python 3.7+
- Raspbian/Raspberry Pi OS
```

### Python Dependencies
```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
RPi.GPIO>=0.7.1
pyserial>=3.5
requests>=2.28.0
joblib>=1.2.0
numpy>=1.21.0
scikit-learn>=1.0.0  # if training/using ML model
```

### Web Server
- Node.js/Python backend (not included in this repo)
- Must implement the API endpoints listed below

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/aahmdakml/Soil-Monitoring-Controlled-Irrigation.git
cd Soil-Monitoring-Controlled-Irrigation
```

### 2. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Enable Serial Port on Raspberry Pi
```bash
sudo raspi-config
# Navigate to:   Interface Options → Serial Port
# - Login shell over serial:   NO
# - Serial port hardware: YES
```

Reboot after changes:  
```bash
sudo reboot
```

### 4. Prepare ML Model
The ML model file (`smart_watering_model.pkl`) is included in this repository. The model is a Random Forest classifier with ~85% accuracy, trained on the dataset mentioned below.

### 5. Configure the System
Edit `rpiML.py` to set your server IP and device ID:
```python
DEVICE_ID = "raspi-1"  # Change to your device identifier
SERVER_BASE = "http://10.3.74.50:8000"  # Change to your server IP
```

## ⚙️ Configuration

### Key Configuration Parameters

#### Timing Intervals (seconds)
```python
PUBLISH_INTERVAL_SECONDS = 15.0    # Sensor data upload frequency
COMMAND_INTERVAL_SECONDS = 5.0     # Remote command polling frequency
SCHEDULE_INTERVAL_SECONDS = 60.0   # Schedule update frequency
REMOTE_TIMEOUT_SECONDS = 30.0      # Remote control timeout
```

#### Serial Communication
```python
SERIAL_PORT = "/dev/serial0"  # RPi serial port
BAUD_RATE = 115200           # Must match ESP32 baud rate
```

#### Sensor Thresholds (Fallback Logic)
```python
SOIL_THRESHOLD = 1800  # Soil moisture (higher = drier)
HUM_MAX = 70          # Maximum humidity (%)
LIGHT_MIN = 300       # Minimum light level
```

#### GPIO Pins
```python
RELAY_PIN = 13  # Water pump relay
SERVO_PIN = 12  # Valve servo (PWM)
```

#### Servo Duty Cycles
```python
DUTY_CYCLE_OFF = 1.5       # Valve closed
DUTY_CYCLE_HALF_ON = 3.4   # Valve half open
DUTY_CYCLE_ON = 6.8        # Valve fully open
```

## 🚀 Usage

### Starting the System

#### Manual Start
```bash
python3 rpiML.py
```

#### Run as System Service (Recommended)
Create a systemd service file:
```bash
sudo nano /etc/systemd/system/irrigation.service
```

Add the following content:
```ini
[Unit]
Description=Smart Irrigation System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Soil-Monitoring-Controlled-Irrigation
ExecStart=/usr/bin/python3 /home/pi/Soil-Monitoring-Controlled-Irrigation/rpiML.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:  
```bash
sudo systemctl daemon-reload
sudo systemctl enable irrigation.service
sudo systemctl start irrigation.service
```

Check status:
```bash
sudo systemctl status irrigation.service
```

View logs:
```bash
journalctl -u irrigation.service -f
```

### Stopping the System
```bash
# If running manually
Ctrl+C

# If running as service
sudo systemctl stop irrigation.service
```

## 🎮 Control Modes

### 1. LOCAL/AUTO Mode (Priority 3)
**Default operational mode** - system makes autonomous decisions

#### Decision Logic Flow:  
```
1. Check if ML model is available
   ├─ YES: Use ML prediction (temp, humidity, light, soil, hour)
   └─ NO: Use rule-based fallback:  
          WATER_ON if:  
          - Soil is dry (> SOIL_THRESHOLD)
          - Air is dry (< HUM_MAX)
          - Light is sufficient (> LIGHT_MIN)
```

**Activation:**
- Default at startup
- After REMOTE control timeout (30s)
- Via mode command from web server

### 2. SCHEDULE Mode (Priority 2)
**Time-based automated watering**

#### Features:
- Executes at specific times (HH:MM format)
- Configurable duration (seconds)
- Prevents duplicate execution on same day
- Fetched from web server every 60 seconds

#### Schedule Format (JSON):
```json
{
  "time": "07:00",
  "duration_sec": 300,
  "enabled": true
}
```

**Behavior:**
- Starts watering at scheduled time
- Runs for specified duration
- Automatically stops and returns to LOCAL mode
- Overrides LOCAL mode during execution
- Does NOT run in REMOTE mode

### 3. REMOTE Mode (Priority 1)
**Manual control via web interface** - highest priority

#### Features:
- Direct pump ON/OFF control
- Servo position control (OPEN/HALF_OPEN/CLOSE)
- Overrides all other modes
- 30-second timeout (returns to LOCAL if no new commands)

**Command Types:**
- `pump`: `{status: "on"|"off"}`
- `servo`: `{position: "open"|"half_open"|"close"}`
- `mode`: `{status: "auto"|"local"|"remote"}`

## 🌐 API Endpoints

### 1.  Sensor Data Upload
**POST** `/api/edge/sensor`

Sends sensor readings and actuator status to server.

**Request Body:**
```json
{
  "device_id": "raspi-1",
  "temperature": 25.5,
  "humidity": 60.2,
  "light": 450,
  "soil_moisture":   1650,
  "auto_decision": "WATER_ON",
  "pump_status": "ON",
  "servo_position":   "OPEN",
  "control_mode": "LOCAL"
}
```

### 2. Fetch Commands
**GET** `/api/edge/commands?device_id=raspi-1`

Retrieves pending remote control commands.

**Response:**
```json
[
  {
    "id":   123,
    "type": "pump",
    "payload": {"status": "on"}
  },
  {
    "id":  124,
    "type": "servo",
    "payload": {"position": "open"}
  }
]
```

### 3. Event Reporting
**POST** `/api/edge/event`

Sends status updates and command acknowledgments.

**Request Body:**
```json
{
  "device_id": "raspi-1",
  "pump_status": "ON",
  "servo_position":   "OPEN",
  "source": "edge",
  "message": "Command 123 executed",
  "command_id": 123
}
```

### 4. Fetch Schedule
**GET** `/api/schedule?device_id=raspi-1`

Retrieves watering schedule from server.

**Response (Single):**
```json
{
  "time_hhmm": "07:00",
  "duration_seconds": 300,
  "enabled": true
}
```

**Response (Multiple):**
```json
[
  {
    "time": "07:00",
    "duration_sec": 300
  },
  {
    "time": "17:00",
    "duration_sec": 180
  }
]
```

## 🧠 ML Model

### Model Overview
- **Type**: Random Forest Classifier
- **Accuracy**: ~85%
- **File**: `smart_watering_model.pkl`
- **Framework**: scikit-learn

### Model Input Features
The ML model expects 5 features:
1. **Temperature** (°C)
2. **Humidity** (%)
3. **Light** intensity (analog value)
4. **Soil Moisture** (analog value)
5. **Current Hour** (0-23)

### Model Output
- **1** or `"WATER_ON"`: Activate watering
- **0** or `"WATER_OFF"`: Deactivate watering

### Training Your Own Model
```python
import joblib
from sklearn.ensemble import RandomForestClassifier

# Example training code
features = [[temp, humidity, light, soil, hour], ...]
labels = [1, 0, 1, ...]  # 1 = water, 0 = no water

model = RandomForestClassifier()
model.fit(features, labels)

# Save model
joblib.dump(model, 'smart_watering_model.pkl')
```

### Fallback Behavior
If model fails to load or predict: 
- System automatically uses rule-based threshold logic
- Warning logged:   `[ML-WARN] Local decision logic will use threshold rules`

## 📊 Dataset

The machine learning model was trained using the **Plant Watering Prediction Dataset** from Kaggle: 

**Dataset Source**: [Dataset for Predicting Watering the Plants](https://www.kaggle.com/datasets/nelakurthisudheer/dataset-for-predicting-watering-the-plants)

### Dataset Features
The dataset includes the following sensor readings:
- **Temperature**:  Ambient temperature in Celsius
- **Humidity**:  Relative humidity percentage
- **Light**:  Light intensity levels
- **Soil Moisture**:  Soil moisture sensor readings
- **Time**: Hour of the day (0-23)
- **Target**: Binary classification (1 = needs water, 0 = doesn't need water)

### Dataset Usage
The included dataset can be used to:
- Retrain the model with your own parameters
- Validate model performance
- Understand the training data distribution
- Experiment with different ML algorithms

## 🐛 Troubleshooting

### Serial Communication Issues
```bash
# Check if serial port exists
ls -l /dev/serial0

# Test serial connection
minicom -b 115200 -o -D /dev/serial0

# Check for serial permissions
sudo usermod -a -G dialout $USER
# Logout and login again
```

### GPIO Permission Errors
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER

# Or run with sudo (not recommended for production)
sudo python3 rpiML.py
```

### Web Server Connection Failed
```bash
# Test server connectivity
ping 10.3.74.50  # Replace with your server IP

# Test API endpoint
curl http://10.3.74.50:8000/api/edge/commands?device_id=raspi-1
```

### ML Model Not Loading
```bash
# Verify model file exists
ls -l smart_watering_model.pkl

# Check Python version compatibility
python3 --version

# Reinstall joblib and sklearn
pip3 install --upgrade joblib scikit-learn
```

### Servo Not Moving
- Check PWM signal on GPIO 12 with oscilloscope/multimeter
- Verify servo power supply (most servos need 5V)
- Adjust duty cycle values if using different servo model

### System Logs
```bash
# View real-time logs
journalctl -u irrigation.service -f

# View last 100 lines
journalctl -u irrigation.service -n 100

# View logs from today
journalctl -u irrigation.service --since today
```

## 📊 Example Output

### Successful Startup
```
[ML-INFO] Successfully loaded ML model:   smart_watering_model.pkl
[GPIO] RPi Actuators Ready.  
[INFO] Serial opened:   /dev/serial0 @ 115200
[INFO] Starting RPi Gateway Web Client.   ID: raspi-1

[SENSOR READ] New data received:  {'temp': '25.3', 'hum': '62.1', 'light': '480', 'soil': '1750'}
[DEBUG-LOGIC] ML Model Decision: WATER_ON
[ACTION] Pump:   ON (HIGH)
[SERVO] Moved to 6.80% DC.  

--- PUBLISH SENSOR CYCLE TO WEB (15s) ---
[EVENT] Status report sent successfully

[SCHEDULE-START] Starting scheduled watering for 300 seconds at 07:00.
```

---

**Made with 🌱 for smart agriculture and sustainable farming**
