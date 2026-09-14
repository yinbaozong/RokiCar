import gc
import math
import network
import socket
import time
from machine import Pin, PWM

try:
    import ujson as json
except ImportError:
    import json


AP_SSID = "OmniCar"
AP_PASSWORD = "12345678"
AP_IP = "192.168.4.1"

# CyberBrick Controller Core pin plan:
# S1/S2/S3/S4 signal pins are GPIO3/GPIO2/GPIO1/GPIO0.
# GPIO21/GPIO20 are used for the third motor on core-board side pads.
MOTOR_PINS = {
    "w1_left_front": (3, 2),   # DRV-A AIN1/AIN2
    "w2_right_front": (1, 0),  # DRV-A BIN1/BIN2
    "w3_rear": (21, 20),      # DRV-B AIN1/AIN2
}

# Change these signs if a wheel spins in the opposite direction during testing.
MOTOR_SIGN = {
    "w1_left_front": 1,
    "w2_right_front": 1,
    "w3_rear": 1,
}

PWM_FREQ = 1000
PWM_MAX = 65535
SPEED_LIMIT = 0.45       # First floor test: keep 0.35-0.50
ROT_GAIN = 0.75
COMMAND_TIMEOUT_MS = 500


HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
  <title>OmniCar Control</title>
  <style>
    * { box-sizing: border-box; touch-action: manipulation; }
    body { margin: 0; font-family: Arial, sans-serif; background: #f6f7f2; color: #1f2428; }
    main { min-height: 100vh; padding: 18px; display: grid; gap: 14px; align-content: start; }
    h1 { margin: 0; font-size: 26px; }
    h2 { margin: 0 0 10px; font-size: 18px; }
    .hint { color: #667078; line-height: 1.5; margin: 6px 0 0; }
    .card { background: #fff; border: 1px solid #d7ddd8; border-radius: 8px; padding: 14px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    button {
      min-height: 58px; border: 1px solid #aeb8b2; border-radius: 8px;
      background: #ffffff; font-size: 18px; color: #1f2428;
    }
    button:active { background: #dff3e8; transform: translateY(1px); }
    .stop { background: #fff0ed; border-color: #d8a8a0; }
    label { display: grid; grid-template-columns: 64px 1fr 48px; gap: 10px; align-items: center; margin: 8px 0; }
    input[type="range"] { width: 100%; accent-color: #168a5b; }
    .status { font-family: Consolas, monospace; white-space: pre-wrap; line-height: 1.5; }
  </style>
</head>
<body>
<main>
  <section>
    <h1>OmniCar</h1>
    <p class="hint">CyberBrick + DRV8833 三轮全向底盘测试。第一次请把车架空。</p>
  </section>

  <section class="card">
    <h2>移动</h2>
    <div class="grid">
      <button data-vx="-0.5" data-vy="0.5" data-rot="0">左前</button>
      <button data-vx="0" data-vy="0.7" data-rot="0">前进</button>
      <button data-vx="0.5" data-vy="0.5" data-rot="0">右前</button>
      <button data-vx="-0.7" data-vy="0" data-rot="0">左移</button>
      <button class="stop" data-vx="0" data-vy="0" data-rot="0">停止</button>
      <button data-vx="0.7" data-vy="0" data-rot="0">右移</button>
      <button data-vx="0" data-vy="0" data-rot="-0.7">左转</button>
      <button data-vx="0" data-vy="-0.7" data-rot="0">后退</button>
      <button data-vx="0" data-vy="0" data-rot="0.7">右转</button>
    </div>
  </section>

  <section class="card">
    <h2>微调</h2>
    <label>Vx <input id="vx" type="range" min="-1" max="1" step="0.05" value="0"><span id="vxv">0</span></label>
    <label>Vy <input id="vy" type="range" min="-1" max="1" step="0.05" value="0"><span id="vyv">0</span></label>
    <label>Rot <input id="rot" type="range" min="-1" max="1" step="0.05" value="0"><span id="rotv">0</span></label>
    <button id="send">发送</button>
  </section>

  <section class="card">
    <div id="status" class="status">未连接</div>
  </section>
</main>

<script>
const statusBox = document.getElementById("status");
const sliders = ["vx", "vy", "rot"].map(id => document.getElementById(id));

function updateLabels() {
  document.getElementById("vxv").textContent = document.getElementById("vx").value;
  document.getElementById("vyv").textContent = document.getElementById("vy").value;
  document.getElementById("rotv").textContent = document.getElementById("rot").value;
}

async function send(vx, vy, rot) {
  try {
    const res = await fetch(`/cmd?vx=${vx}&vy=${vy}&rot=${rot}&t=${Date.now()}`);
    const data = await res.json();
    statusBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    statusBox.textContent = "请求失败: " + err;
  }
}

document.querySelectorAll("button[data-vx]").forEach(btn => {
  btn.addEventListener("click", () => {
    document.getElementById("vx").value = btn.dataset.vx;
    document.getElementById("vy").value = btn.dataset.vy;
    document.getElementById("rot").value = btn.dataset.rot;
    updateLabels();
    send(btn.dataset.vx, btn.dataset.vy, btn.dataset.rot);
  });
});

sliders.forEach(slider => slider.addEventListener("input", updateLabels));
document.getElementById("send").addEventListener("click", () => {
  send(document.getElementById("vx").value, document.getElementById("vy").value, document.getElementById("rot").value);
});
updateLabels();
setInterval(() => send(0, 0, 0), 2000);
</script>
</body>
</html>
"""


class Motor:
    def __init__(self, pin_a, pin_b, sign=1):
        self.a = PWM(Pin(pin_a), freq=PWM_FREQ)
        self.b = PWM(Pin(pin_b), freq=PWM_FREQ)
        self.sign = sign
        self.set(0)

    def _duty(self, value):
        value = max(0, min(1, abs(value)))
        return int(PWM_MAX * value)

    def _write(self, pwm, value):
        duty = self._duty(value)
        if hasattr(pwm, "duty_u16"):
            pwm.duty_u16(duty)
        else:
            pwm.duty(int(duty * 1023 / PWM_MAX))

    def set(self, speed):
        speed = max(-1, min(1, speed * self.sign))
        if speed > 0:
            self._write(self.a, speed)
            self._write(self.b, 0)
        elif speed < 0:
            self._write(self.a, 0)
            self._write(self.b, -speed)
        else:
            self._write(self.a, 0)
            self._write(self.b, 0)


motors = {
    name: Motor(pins[0], pins[1], MOTOR_SIGN[name])
    for name, pins in MOTOR_PINS.items()
}

state = {
    "vx": 0,
    "vy": 0,
    "rot": 0,
    "w1": 0,
    "w2": 0,
    "w3": 0,
    "limit": SPEED_LIMIT,
    "count": 0,
    "last_ms": 0,
}


def stop_all():
    for motor in motors.values():
        motor.set(0)
    state["w1"] = 0
    state["w2"] = 0
    state["w3"] = 0


def mix_omni(vx, vy, rot):
    w1 = -0.5 * vx - 0.866 * vy + ROT_GAIN * rot
    w2 = -0.5 * vx + 0.866 * vy + ROT_GAIN * rot
    w3 =  1.0 * vx              + ROT_GAIN * rot
    scale = max(1, abs(w1), abs(w2), abs(w3))
    return (w1 / scale, w2 / scale, w3 / scale)


def drive(vx, vy, rot):
    w1, w2, w3 = mix_omni(vx, vy, rot)
    w1 *= SPEED_LIMIT
    w2 *= SPEED_LIMIT
    w3 *= SPEED_LIMIT
    motors["w1_left_front"].set(w1)
    motors["w2_right_front"].set(w2)
    motors["w3_rear"].set(w3)
    state["vx"] = round(vx, 3)
    state["vy"] = round(vy, 3)
    state["rot"] = round(rot, 3)
    state["w1"] = round(w1, 3)
    state["w2"] = round(w2, 3)
    state["w3"] = round(w3, 3)
    state["count"] += 1
    state["last_ms"] = time.ticks_ms()


def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    try:
        ap.config(essid=AP_SSID, password=AP_PASSWORD, authmode=network.AUTH_WPA_WPA2_PSK)
    except Exception:
        ap.config(essid=AP_SSID, password=AP_PASSWORD)
    ap.ifconfig((AP_IP, "255.255.255.0", AP_IP, AP_IP))
    while not ap.active():
        time.sleep(0.1)
    return ap


def parse_query(path):
    values = {}
    if "?" not in path:
        return values
    query = path.split("?", 1)[1].split(" ", 1)[0]
    for part in query.split("&"):
        if "=" in part:
            key, value = part.split("=", 1)
            values[key] = value
    return values


def response(conn, status, content_type, body):
    if isinstance(body, str):
        body = body.encode("utf-8")
    header = (
        "HTTP/1.1 {}\r\n"
        "Content-Type: {}\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-store\r\n\r\n"
    ).format(status, content_type, len(body))
    conn.send(header.encode("utf-8"))
    conn.send(body)


def handle_request(conn):
    request = conn.recv(1024).decode()
    first = request.split("\r\n", 1)[0]
    path = first.split(" ")[1] if " " in first else "/"

    if path.startswith("/cmd"):
        q = parse_query(first)
        vx = float(q.get("vx", 0))
        vy = float(q.get("vy", 0))
        rot = float(q.get("rot", 0))
        drive(vx, vy, rot)
        response(conn, "200 OK", "application/json", json.dumps(state))
    else:
        response(conn, "200 OK", "text/html; charset=utf-8", HTML)


def main():
    stop_all()
    ap = start_ap()
    print("AP:", AP_SSID, AP_PASSWORD, ap.ifconfig())

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(2)
    server.settimeout(0.2)
    print("Open http://{}/".format(AP_IP))

    while True:
        try:
            conn, _ = server.accept()
            try:
                handle_request(conn)
            finally:
                conn.close()
                gc.collect()
        except OSError:
            pass

        if state["last_ms"] and time.ticks_diff(time.ticks_ms(), state["last_ms"]) > COMMAND_TIMEOUT_MS:
            stop_all()
            state["last_ms"] = 0


main()
