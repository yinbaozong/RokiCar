"""Pure control logic shared by the CyberBrick firmware and CPython tests."""

try:
    import struct
except ImportError:
    struct = None


PROTOCOL_VERSION = 1
MSG_DRIVE = 1
MSG_STOP = 2
MSG_SQUARE = 3
MSG_GAINS = 4
MSG_SAVE = 5
MSG_PING = 6
MSG_WHEEL_MAP = 7
MSG_WHEEL_TEST = 8
MSG_MOTOR_TEST = 9
MSG_MOTOR_MODEL = 10
MSG_QUERY_CONFIG = 11
FRAME_SIZE = 12

GAIN_MIN = 700
GAIN_MAX = 1300
WHEEL_TEST_MIN_MS = 50
WHEEL_TEST_MAX_MS = 5000
MOTOR_TEST_MIN_MS = 100
MOTOR_TEST_MAX_MS = 3000
MIN_DUTY_MAX = 350


def clamp(value, low, high):
    return max(low, min(high, value))


def linearize_motor_command(value, min_duty, max_duty=0.45):
    """Map desired wheel speed through the measured static-friction deadzone."""
    value = clamp(float(value), -1.0, 1.0)
    if abs(value) < 0.0001:
        return 0
    minimum = clamp(float(min_duty), 0.0, float(max_duty))
    duty = minimum + abs(value) * (float(max_duty) - minimum)
    return duty if value > 0 else -duty


def normalize_wheels(vx, vy, rot, rot_gain, gains):
    """Return three normalized wheel commands after applying calibration gains."""
    # Positive rotation is the human-facing "turn right" / clockwise command.
    w1 = -0.5 * vx - 0.8660254 * vy - rot_gain * rot
    w2 = -0.5 * vx + 0.8660254 * vy - rot_gain * rot
    w3 = vx - rot_gain * rot
    w1 *= gains[0]
    w2 *= gains[1]
    w3 *= gains[2]
    scale = max(1.0, abs(w1), abs(w2), abs(w3))
    return w1 / scale, w2 / scale, w3 / scale


def validate_gains(values):
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return (1000, 1000, 1000)
    result = []
    for value in values:
        try:
            value = int(value)
        except Exception:
            return (1000, 1000, 1000)
        if value < GAIN_MIN or value > GAIN_MAX:
            return (1000, 1000, 1000)
        result.append(value)
    return tuple(result)


def gains_as_float(gains):
    return tuple(value / 1000.0 for value in validate_gains(gains))


def validate_wheel_map(values):
    """Map kinematic W1/W2/W3 to signed physical motor ports +/-1..3."""
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return (1, 2, 3)
    try:
        result = tuple(int(value) for value in values)
    except Exception:
        return (1, 2, 3)
    if set(abs(value) for value in result) != {1, 2, 3} or any(value == 0 for value in result):
        return (1, 2, 3)
    return result


def validate_wheel_test(port, speed, duration):
    try:
        port, speed, duration = int(port), int(speed), abs(int(duration))
    except Exception:
        return None
    if not 1 <= port <= 3 or not WHEEL_TEST_MIN_MS <= duration <= WHEEL_TEST_MAX_MS:
        return None
    return port - 1, clamp(speed, -300, 300), duration


def validate_motor_test(port, duty, duration):
    try:
        port, duty, duration = int(port), int(duty), abs(int(duration))
    except Exception:
        return None
    if not 1 <= port <= 3 or not MOTOR_TEST_MIN_MS <= duration <= MOTOR_TEST_MAX_MS:
        return None
    duty = clamp(duty, -MIN_DUTY_MAX, MIN_DUTY_MAX)
    if 0 < abs(duty) < 50:
        duty = 50 if duty > 0 else -50
    return port - 1, duty, duration


def validate_min_duties(values):
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return (0, 0, 0)
    try:
        result = tuple(int(value) for value in values)
    except Exception:
        return (0, 0, 0)
    if any(value < 0 or value > MIN_DUTY_MAX for value in result):
        return (0, 0, 0)
    return result


def is_newer_sequence(sequence, previous):
    if previous is None:
        return True
    delta = (sequence - previous) & 0xffffffff
    return delta != 0 and delta < 0x80000000


def decode_command(payload):
    if struct is None or len(payload) != FRAME_SIZE:
        return None
    try:
        version, msg_type, sequence, x, y, z = struct.unpack("<BBIhhh", payload)
    except Exception:
        return None
    if version != PROTOCOL_VERSION:
        return None
    return msg_type, sequence, x, y, z


def encode_command(msg_type, sequence, x=0, y=0, z=0):
    return struct.pack("<BBIhhh", PROTOCOL_VERSION, msg_type, sequence, x, y, z)


class SquareRunner:
    """Non-blocking four-leg square motion. Coordinates: forward, right, back, left."""

    def __init__(self, leg_ms=1600, pause_ms=250, speed=550):
        self.leg_ms = leg_ms
        self.pause_ms = pause_ms
        self.speed = speed
        self.running = False
        self.leg = 0
        self.pausing = False
        self.deadline = 0

    def start(self, now_ms):
        self.running = True
        self.leg = 0
        self.pausing = False
        self.deadline = now_ms + self.leg_ms

    def stop(self):
        self.running = False

    def update(self, now_ms):
        if not self.running:
            return 0, 0, 0, False
        while now_ms >= self.deadline:
            if self.pausing:
                self.leg += 1
                if self.leg >= 4:
                    self.running = False
                    return 0, 0, 0, False
                self.pausing = False
                self.deadline += self.leg_ms
            else:
                self.pausing = True
                self.deadline += self.pause_ms
        if self.pausing:
            return 0, 0, 0, True
        directions = ((0, self.speed, 0), (self.speed, 0, 0),
                      (0, -self.speed, 0), (-self.speed, 0, 0))
        vx, vy, rot = directions[self.leg]
        return vx, vy, rot, True
