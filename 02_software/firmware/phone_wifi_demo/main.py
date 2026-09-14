import gc
import network
import socket
import time
from machine import Pin

try:
    import neopixel
except ImportError:
    neopixel = None

try:
    import ujson as json
except ImportError:
    import json


AP_SSID = "OmniCar-Demo"
AP_PASSWORD = "12345678"
AP_IP = "192.168.4.1"
LED_PIN = 8


led_pin = Pin(LED_PIN, Pin.OUT)
pixel = neopixel.NeoPixel(led_pin, 1) if neopixel else None
state = {
    "vx": 0,
    "vy": 0,
    "rot": 0,
    "rgb": [0, 0, 0],
    "last": 0,
    "count": 0,
}


HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
  <title>CyberBrick LED Demo</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Arial, sans-serif; background: #f6f7f2; color: #1f2428; }
    main { min-height: 100vh; padding: 18px; display: grid; gap: 14px; align-content: start; }
    h1 { margin: 0; font-size: 26px; }
    .card { background: #fff; border: 1px solid #d7ddd8; border-radius: 8px; padding: 14px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .colors { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 12px; }
    button {
      min-height: 58px; border: 1px solid #aeb8b2; border-radius: 8px;
      background: #ffffff; font-size: 18px; color: #1f2428;
    }
    button:active { background: #dff3e8; transform: translateY(1px); }
    .wide { grid-column: span 3; }
    .status { font-family: Consolas, monospace; white-space: pre-wrap; line-height: 1.5; }
    .hint { color: #667078; line-height: 1.5; margin: 0; }
    input[type="range"] { width: 100%; accent-color: #168a5b; }
    label { display: grid; grid-template-columns: 36px 1fr 42px; gap: 10px; align-items: center; }
  </style>
</head>
<body>
<main>
  <section>
    <h1>CyberBrick LED Demo</h1>
    <p class="hint">手机已连到 CyberBrick 热点。这个页面控制核心板板载 RGB 指示灯，不驱动电机。</p>
  </section>
  <section class="card">
    <h2>指示灯颜色</h2>
    <div class="colors">
      <button data-r="255" data-g="0" data-b="0">红</button>
      <button data-r="0" data-g="255" data-b="0">绿</button>
      <button data-r="0" data-g="0" data-b="255">蓝</button>
      <button data-r="255" data-g="180" data-b="0">黄</button>
      <button data-r="255" data-g="255" data-b="255">白</button>
      <button data-r="0" data-g="0" data-b="0">关</button>
    </div>
  </section>
  <section class="card">
    <h2>自定义 RGB</h2>
    <label>R <input id="r" type="range" min="0" max="255" value="0"><span id="rv">0</span></label>
    <label>G <input id="g" type="range" min="0" max="255" value="0"><span id="gv">0</span></label>
    <label>B <input id="b" type="range" min="0" max="255" value="0"><span id="bv">0</span></label>
    <button class="wide" id="apply">应用颜色</button>
  </section>
  <section class="card">
    <h2>控制请求测试</h2>
    <div class="grid">
      <button></button>
      <button data-vx="0" data-vy="1" data-rot="0">前进</button>
      <button></button>
      <button data-vx="-1" data-vy="0" data-rot="0">左移</button>
      <button data-vx="0" data-vy="0" data-rot="0">停止</button>
      <button data-vx="1" data-vy="0" data-rot="0">右移</button>
      <button data-vx="0" data-vy="0" data-rot="-1">左转</button>
      <button data-vx="0" data-vy="-1" data-rot="0">后退</button>
      <button data-vx="0" data-vy="0" data-rot="1">右转</button>
      <button class="wide" id="ping">Ping / 闪灯</button>
    </div>
  </section>
  <section class="card">
    <div id="status" class="status">连接中...</div>
  </section>
</main>
<script>
const statusBox = document.getElementById("status");

async function setLed(r, g, b) {
  try {
    const res = await fetch(`/led?r=${r}&g=${g}&b=${b}&t=${Date.now()}`);
    const data = await res.json();
    statusBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    statusBox.textContent = "请求失败: " + err;
  }
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
    send(btn.dataset.vx, btn.dataset.vy, btn.dataset.rot);
  });
});

document.querySelectorAll("button[data-r]").forEach(btn => {
  btn.addEventListener("click", () => {
    const r = Number(btn.dataset.r);
    const g = Number(btn.dataset.g);
    const b = Number(btn.dataset.b);
    document.getElementById("r").value = r;
    document.getElementById("g").value = g;
    document.getElementById("b").value = b;
    updateLabels();
    setLed(r, g, b);
  });
});

function updateLabels() {
  document.getElementById("rv").textContent = document.getElementById("r").value;
  document.getElementById("gv").textContent = document.getElementById("g").value;
  document.getElementById("bv").textContent = document.getElementById("b").value;
}

["r", "g", "b"].forEach(id => document.getElementById(id).addEventListener("input", updateLabels));
document.getElementById("apply").addEventListener("click", () => {
  setLed(document.getElementById("r").value, document.getElementById("g").value, document.getElementById("b").value);
});

document.getElementById("ping").addEventListener("click", () => send(0, 0, 0));
updateLabels();
</script>
</body>
</html>
"""


def blink(times=1, delay=0.08):
    for _ in range(times):
        set_rgb(0, 32, 0)
        time.sleep(delay)
        set_rgb(0, 0, 0)
        time.sleep(delay)


def set_rgb(r, g, b):
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    state["rgb"] = [r, g, b]
    if pixel:
        pixel[0] = (r, g, b)
        pixel.write()
    else:
        led_pin.value(1 if (r or g or b) else 0)


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


def main():
    blink(2)
    ap = start_ap()
    print("AP started:", AP_SSID, AP_PASSWORD, ap.ifconfig())

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(2)
    print("Open http://{}/".format(AP_IP))

    while True:
        conn = None
        try:
            conn, _ = server.accept()
            try:
                request = conn.recv(1024).decode()
            except Exception:
                request = ""
            first = request.split("\r\n", 1)[0]
            path = first.split(" ")[1] if " " in first else "/"

            if path.startswith("/cmd"):
                q = parse_query(first)
                state["vx"] = int(float(q.get("vx", 0)) * 100)
                state["vy"] = int(float(q.get("vy", 0)) * 100)
                state["rot"] = int(float(q.get("rot", 0)) * 100)
                state["last"] = time.ticks_ms()
                state["count"] += 1
                blink(1, 0.03)
                response(conn, "200 OK", "application/json", json.dumps(state))
            elif path.startswith("/led"):
                q = parse_query(first)
                set_rgb(q.get("r", 0), q.get("g", 0), q.get("b", 0))
                state["last"] = time.ticks_ms()
                state["count"] += 1
                response(conn, "200 OK", "application/json", json.dumps(state))
            else:
                response(conn, "200 OK", "text/html; charset=utf-8", HTML)
        except Exception as exc:
            print("server error:", exc)
        finally:
            if conn:
                conn.close()
            gc.collect()


main()
