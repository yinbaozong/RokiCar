import gc
import os
import time

try:
    import usocket as socket
except ImportError:
    import socket
try:
    import ujson as json
except ImportError:
    import json
try:
    import ubinascii as binascii
except ImportError:
    import binascii
try:
    import uhashlib as hashlib
except ImportError:
    import hashlib
try:
    import neopixel
except ImportError:
    neopixel = None

import machine
from machine import Pin, PWM, WDT
from rokicar_core import (
    MSG_DRIVE, MSG_GAINS, MSG_PING, MSG_SAVE, MSG_SQUARE, MSG_STOP,
    MSG_WHEEL_MAP, MSG_WHEEL_TEST, MSG_MOTOR_TEST, MSG_MOTOR_MODEL,
    MSG_QUERY_CONFIG,
    SquareRunner, decode_command, gains_as_float, is_newer_sequence,
    linearize_motor_command, normalize_wheels, validate_gains,
    validate_min_duties, validate_motor_test, validate_wheel_map,
    validate_wheel_test,
)

AP_SSID = "RokiCar"
AP_PASSWORD = "12345678"
AP_IP = "192.168.4.1"
RGB_LED_PIN = 8
ACCESSORY_LED_PIN = 3  # S1; D1/D2 remain assigned to W3.
MSG_LIGHT = 12
accessory_rgb = (0, 0, 0)
accessory_led = None
try:
    if neopixel:
        accessory_led = neopixel.NeoPixel(Pin(ACCESSORY_LED_PIN), 4)
        accessory_led.fill(accessory_rgb)
        accessory_led.write()
except Exception:
    accessory_led = None
M1_AIN1, M1_AIN2 = 4, 5
M2_AIN1, M2_AIN2 = 6, 7
W3_AIN1, W3_AIN2 = 21, 20

PWM_FREQ = 1000
PWM_MAX = 65535
SPEED_LIMIT = 0.45
ROT_GAIN = 0.75
COMMAND_TIMEOUT_MS = 500
SOCKET_TIMEOUT_S = 0.1
GC_PERIOD_MS = 2000
WDT_TIMEOUT_MS = 2000
CONFIG_PATH = "rokicar_config.json"
CONFIG_TEMP_PATH = "rokicar_config.tmp"
CONFIG_VERSION = 2
MODE_IDLE, MODE_MANUAL, MODE_SQUARE, MODE_TEST = 0, 1, 2, 3


class Led:
    def __init__(self):
        self.last = None
        self.np = None
        self.pin = None
        try:
            self.np = neopixel.NeoPixel(Pin(RGB_LED_PIN), 1) if neopixel else None
            if not self.np:
                self.pin = Pin(RGB_LED_PIN, Pin.OUT)
        except Exception:
            self.pin = None

    def set(self, color):
        if color == self.last:
            return
        self.last = color
        try:
            if self.np:
                self.np[0] = color
                self.np.write()
            elif self.pin:
                self.pin.value(1 if color != (0, 0, 0) else 0)
        except Exception:
            pass


class Motor:
    def __init__(self, first, second):
        self.first = PWM(Pin(first), freq=PWM_FREQ)
        self.second = PWM(Pin(second), freq=PWM_FREQ)
        self.stop()

    def duty(self, pwm, value):
        value = max(0, min(1, value))
        duty = int(PWM_MAX * value)
        if hasattr(pwm, "duty_u16"):
            pwm.duty_u16(duty)
        else:
            pwm.duty(int(duty * 1023 / PWM_MAX))

    def set_raw(self, value):
        if value > 0:
            self.duty(self.first, value)
            self.duty(self.second, 0)
        elif value < 0:
            self.duty(self.first, 0)
            self.duty(self.second, -value)
        else:
            self.stop()

    def set(self, value, min_duty=0):
        self.set_raw(linearize_motor_command(value, min_duty, SPEED_LIMIT))

    def stop(self):
        self.duty(self.first, 0)
        self.duty(self.second, 0)


led = Led()
m1 = Motor(M1_AIN1, M1_AIN2)
m2 = Motor(M2_AIN1, M2_AIN2)
w3 = Motor(W3_AIN1, W3_AIN2)
motors = (m1, m2, w3)
square = SquareRunner(1600, 250, 550)
state = {
    "mode": MODE_IDLE, "gains": (1000, 1000, 1000), "last_cmd": 0,
    "wheel_map": (1, 2, -3), "min_duty": (0, 0, 0), "test_until": 0,
    "vector": (0, 0, 0), "wheels": (0, 0, 0),
    "last_seen": 0,
    "last_seq": None, "received": 0, "dropped": 0, "errors": 0,
    "reset": machine.reset_cause(), "last_error": "",
}
ws_conn = None
ws_buffer = bytearray()
last_gc = 0
wdt = None


def hard_stop():
    m1.stop()
    m2.stop()
    w3.stop()


def stop_all():
    square.stop()
    hard_stop()
    state["mode"] = MODE_IDLE
    state["vector"] = (0, 0, 0)
    state["wheels"] = (0, 0, 0)


def drive(vx, vy, rot):
    wheels = normalize_wheels(vx / 1000.0, vy / 1000.0, rot / 1000.0,
                              ROT_GAIN, gains_as_float(state["gains"]))
    physical = [0, 0, 0]
    for wheel, mapping in enumerate(state["wheel_map"]):
        physical[abs(mapping) - 1] = wheels[wheel] * (1 if mapping > 0 else -1)
    for index, value in enumerate(physical):
        motors[index].set(value, state["min_duty"][index] / 1000.0)
    state["vector"] = (vx, vy, rot)
    state["wheels"] = tuple(int(value * 1000) for value in physical)


def load_config():
    try:
        with open(CONFIG_PATH, "r") as file:
            config = json.loads(file.read())
            state["gains"] = validate_gains(config.get("gains"))
            mapping = validate_wheel_map(config.get("wheel_map"))
            if int(config.get("version", 1)) < CONFIG_VERSION:
                mapping = tuple(-value if abs(value) == 3 else value for value in mapping)
            state["wheel_map"] = mapping
            state["min_duty"] = validate_min_duties(config.get("min_duty"))
            if int(config.get("version", 1)) < CONFIG_VERSION:
                save_config()
    except Exception:
        state["gains"] = (1000, 1000, 1000)
        state["wheel_map"] = (1, 2, -3)
        state["min_duty"] = (0, 0, 0)


def save_config():
    try:
        with open(CONFIG_TEMP_PATH, "w") as file:
            file.write(json.dumps({"version": CONFIG_VERSION,
                                   "gains": list(state["gains"]),
                                   "wheel_map": list(state["wheel_map"]),
                                   "min_duty": list(state["min_duty"])}))
        try:
            os.rename(CONFIG_TEMP_PATH, CONFIG_PATH)
        except OSError:
            try:
                os.remove(CONFIG_PATH)
            except OSError:
                pass
            os.rename(CONFIG_TEMP_PATH, CONFIG_PATH)
        return True
    except Exception:
        state["errors"] += 1
        return False


def start_ap():
    import network
    ap = network.WLAN(network.AP_IF)
    try:
        ap.active(False)
        time.sleep_ms(100)
    except Exception:
        pass
    ap.active(True)
    try:
        ap.config(essid=AP_SSID, password=AP_PASSWORD, authmode=network.AUTH_WPA_WPA2_PSK)
    except Exception:
        ap.config(essid=AP_SSID, password=AP_PASSWORD)
    ap.ifconfig((AP_IP, "255.255.255.0", AP_IP, AP_IP))


def write_all(conn, data, timeout=0.2):
    try:
        conn.settimeout(timeout)
        conn.write(data)
        conn.settimeout(SOCKET_TIMEOUT_S)
        return True
    except Exception:
        return False


def reply(conn, status, content_type, body=b""):
    if isinstance(body, str):
        body = body.encode()
    header = "HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n".format(status, content_type, len(body)).encode()
    write_all(conn, header + body)


def status_text():
    now = time.ticks_ms()
    age = 0 if state["mode"] == MODE_IDLE else max(0, time.ticks_diff(now, state["last_cmd"]))
    return json.dumps({"m": state["mode"], "a": age, "r": state["received"],
                       "d": state["dropped"], "h": gc.mem_free(), "c": state["reset"],
                        "g": list(state["gains"]), "p": list(state["wheel_map"]),
                        "n": list(state["min_duty"]),
                        "v": list(state["vector"]), "w": list(state["wheels"]),
                        "e": state["errors"], "x": state["last_error"], "q": state["last_seq"] or 0})


def ws_send(opcode, payload=b""):
    if not ws_conn or len(payload) >= 126:
        return False
    return write_all(ws_conn, bytes((0x80 | opcode, len(payload))) + payload, 0.2)


def handle_command(payload):
    global accessory_rgb
    decoded = decode_command(payload)
    if not decoded:
        state["dropped"] += 1
        return
    msg_type, sequence, x, y, z = decoded
    now = time.ticks_ms()
    state["last_seen"] = now
    if msg_type == MSG_DRIVE:
        if not is_newer_sequence(sequence, state["last_seq"]):
            state["dropped"] += 1
            return
        state["last_seq"] = sequence
        state["last_cmd"] = now
        state["received"] += 1
        square.stop()
        state["mode"] = MODE_MANUAL
        drive(x, y, z)
    elif msg_type == MSG_STOP:
        state["last_cmd"] = now
        stop_all()
    elif msg_type == MSG_SQUARE:
        state["last_cmd"] = now
        square.leg_ms = x if 500 <= x <= 5000 else 1200
        square.speed = max(180, min(650, y if y else 350))
        square.pause_ms = z if 80 <= z <= 1000 else 180
        square.start(now)
        state["mode"] = MODE_SQUARE
    elif msg_type == MSG_GAINS:
        stop_all()
        state["gains"] = validate_gains((x, y, z))
        state["last_cmd"] = now
    elif msg_type == MSG_SAVE:
        save_config()
    elif msg_type == MSG_PING:
        state["last_cmd"] = now
    elif msg_type == MSG_WHEEL_MAP:
        stop_all()
        state["wheel_map"] = validate_wheel_map((x, y, z))
        state["last_cmd"] = now
    elif msg_type == MSG_WHEEL_TEST:
        stop_all()
        test = validate_wheel_test(x, y, z)
        if test:
            port, speed, duration = test
            motors[port].set(speed / 1000.0 * SPEED_LIMIT)
            state["test_until"] = time.ticks_add(now, duration)
            state["mode"] = MODE_TEST
            state["last_cmd"] = now
        else:
            state["dropped"] += 1
    elif msg_type == MSG_MOTOR_TEST:
        stop_all()
        test = validate_motor_test(x, y, z)
        if test:
            port, duty, duration = test
            motors[port].set_raw(duty / 1000.0)
            state["test_until"] = time.ticks_add(now, duration)
            state["mode"] = MODE_TEST
            state["last_cmd"] = now
        else:
            state["dropped"] += 1
    elif msg_type == MSG_MOTOR_MODEL:
        stop_all()
        state["min_duty"] = validate_min_duties((x, y, z))
        state["last_cmd"] = now
    elif msg_type == MSG_LIGHT:
        if accessory_led is not None and all(0 <= c <= 255 for c in (x, y, z)):
            try:
                accessory_led.fill((x, y, z))
                accessory_led.write()
                accessory_rgb = (x, y, z)
                ws_send(1, json.dumps({"light": list(accessory_rgb)}).encode())
            except Exception:
                ws_send(1, b'{"lightError":true}')
        else:
            ws_send(1, b'{"lightError":true}')
    elif msg_type == MSG_QUERY_CONFIG:
        ws_send(1, json.dumps({"g": list(state["gains"]),
                               "light": list(accessory_rgb), "lightReady": accessory_led is not None,
                               "p": list(state["wheel_map"]),
                               "n": list(state["min_duty"])}).encode())
    else:
        state["dropped"] += 1


def process_ws_buffer():
    global ws_buffer
    while len(ws_buffer) >= 2:
        first, second = ws_buffer[0], ws_buffer[1]
        size = second & 0x7f
        if size >= 126 or not (second & 0x80):
            state["errors"] += 1
            state["last_error"] = "bad ws frame"
            return False
        total = 6 + size
        if len(ws_buffer) < total:
            return True
        mask = ws_buffer[2:6]
        payload = bytearray(size)
        for index in range(size):
            payload[index] = ws_buffer[6 + index] ^ mask[index & 3]
        # ESP32-C3 MicroPython does not implement bytearray slice deletion.
        # Frames are tiny and fixed-size, so rebuilding this short remainder
        # is predictable and avoids an unsupported operation.
        ws_buffer = bytearray(ws_buffer[total:])
        opcode = first & 0x0f
        if opcode == 2:
            handle_command(payload)
        elif opcode == 8:
            ws_send(8, payload)
            return False
        elif opcode == 9:
            ws_send(10, payload)
        else:
            state["dropped"] += 1
    return True


def tick():
    global last_gc
    now = time.ticks_ms()
    if state["mode"] == MODE_SQUARE:
        if time.ticks_diff(now, state["last_cmd"]) > COMMAND_TIMEOUT_MS:
            stop_all()
        else:
            vx, vy, rot, running = square.update(now)
            if running:
                drive(vx, vy, rot)
            else:
                stop_all()
    elif state["mode"] == MODE_TEST:
        if time.ticks_diff(now, state["test_until"]) >= 0:
            stop_all()
    elif state["mode"] == MODE_MANUAL and time.ticks_diff(now, state["last_cmd"]) > COMMAND_TIMEOUT_MS:
        stop_all()
    if state["mode"] == MODE_MANUAL:
        led.set((0, 24, 28))
    elif state["mode"] == MODE_SQUARE:
        led.set((22, 0, 28))
    elif ws_conn:
        led.set((0, 18, 0))
    else:
        led.set((14, 8, 0))
    if state["mode"] == MODE_IDLE and time.ticks_diff(now, last_gc) >= GC_PERIOD_MS:
        last_gc = now
        gc.collect()


def close_websocket():
    global ws_conn, ws_buffer
    if ws_conn:
        try:
            ws_conn.close()
        except Exception:
            pass
    ws_conn = None
    ws_buffer = bytearray()


def serve_websocket(conn):
    global ws_conn, ws_buffer
    # Keep the socket non-blocking.  The old implementation stayed inside a
    # recv loop here, which prevented the HTTP server from accepting a page
    # refresh or a new WebSocket connection.
    close_websocket()
    ws_conn = conn
    ws_buffer = bytearray()
    try:
        # This firmware reports b"" for a zero-timeout read, which is
        # indistinguishable from a peer close.  A short finite timeout yields
        # None/OSError for idle sockets while keeping the HTTP accept loop
        # responsive.
        conn.settimeout(SOCKET_TIMEOUT_S)
    except Exception:
        pass
    state["last_seen"] = time.ticks_ms()
    # Sequence numbers are per browser session. A page refresh starts again
    # from 1, so retaining the previous session's value would drop commands.
    state["last_seq"] = None
    state["received"] = 0
    state["dropped"] = 0
    return


def service_websocket():
    if not ws_conn:
        return
    try:
        data = ws_conn.recv(192)
        # None is a non-blocking no-data result; b"" means peer closed.
        if data == b"":
            stop_all()
            close_websocket()
            return
        if data:
            ws_buffer.extend(data)
            if not process_ws_buffer():
                stop_all()
                close_websocket()
    except OSError:
        pass


def upgrade_websocket(conn, request):
    key = None
    for line in request.split("\r\n"):
        if line.lower().startswith("sec-websocket-key:"):
            key = line.split(":", 1)[1].strip()
            break
    if not key:
        reply(conn, "400 Bad Request", "text/plain", "missing websocket key")
        return False
    digest = hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
    accept = binascii.b2a_base64(digest).strip().decode()
    response = ("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: {}\r\n\r\n".format(accept)).encode()
    return write_all(conn, response)


def serve_connection(conn):
    try:
        conn.settimeout(0.3)
        request = conn.recv(1024).decode("utf-8", "ignore")
        if not request:
            return
        first = request.split("\r\n", 1)[0].split(" ")
        path = first[1] if len(first) > 1 else "/"
        if path == "/ws" and upgrade_websocket(conn, request):
            serve_websocket(conn)
            return
        if path.startswith("/health"):
            reply(conn, "200 OK", "application/json", status_text())
        elif path.startswith("/favicon"):
            reply(conn, "204 No Content", "text/plain")
        else:
            reply(conn, "404 Not Found", "application/json", '{"error":"app_only"}')
    except Exception as exc:
        state["errors"] += 1
        state["last_error"] = repr(exc)[:80]
    finally:
        # A successful WebSocket upgrade transfers ownership to the main
        # loop; ordinary HTTP connections remain one-shot.
        if conn is not ws_conn:
            try:
                conn.close()
            except Exception:
                pass


def main():
    global wdt
    hard_stop()
    led.set((20, 20, 20))
    load_config()
    start_ap()
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(socket.getaddrinfo("0.0.0.0", 80)[0][-1])
    server.listen(2)
    server.settimeout(SOCKET_TIMEOUT_S)
    try:
        wdt = WDT(timeout=WDT_TIMEOUT_MS)
    except Exception:
        wdt = None
    stop_all()
    while True:
        if wdt:
            wdt.feed()
        service_websocket()
        try:
            conn, _ = server.accept()
            serve_connection(conn)
        except OSError:
            tick()


try:
    main()
except Exception:
    try:
        hard_stop()
        led.set((40, 0, 0))
    except Exception:
        pass
    raise
