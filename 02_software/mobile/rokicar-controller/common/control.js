export const MESSAGE_TYPES = Object.freeze({
  drive: 1,
  stop: 2,
  square: 3,
  gains: 4,
  save: 5,
  ping: 6,
  wheelMap: 7,
  wheelTest: 8,
});

export const SPEED_LEVELS = Object.freeze({
  slow: 0.35,
  standard: 0.55,
  fast: 0.75,
});

export const TILT_DEFAULTS = Object.freeze({
  deadzone: 3,
  fullScale: 25,
  minNorm: 0.65,
  maxNorm: 1.35,
  alpha: 0.25,
});

export function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

export function anglesFromAcceleration(sample) {
  const x = Number(sample?.x) || 0;
  const y = Number(sample?.y) || 0;
  const z = Number(sample?.z) || 0;
  const toDegrees = 180 / Math.PI;
  const roll = Math.atan2(x, Math.hypot(y, z)) * toDegrees;
  const pitch = Math.atan2(-y, Math.hypot(x, z)) * toDegrees;
  return {
    roll: Object.is(roll, -0) ? 0 : roll,
    pitch: Object.is(pitch, -0) ? 0 : pitch,
    norm: Math.hypot(x, y, z),
  };
}

export function averageNeutral(samples) {
  if (!Array.isArray(samples) || samples.length < 5) return null;
  const total = samples.reduce(
    (sum, sample) => ({ roll: sum.roll + sample.roll, pitch: sum.pitch + sample.pitch }),
    { roll: 0, pitch: 0 },
  );
  return { roll: total.roll / samples.length, pitch: total.pitch / samples.length };
}

export function mapAngleToAxis(angle, deadzone = 3, fullScale = 25) {
  const magnitude = Math.abs(angle);
  if (magnitude <= deadzone) return 0;
  const scaled = clamp((magnitude - deadzone) / (fullScale - deadzone), 0, 1);
  return Math.sign(angle) * scaled;
}

export function updateTilt(sample, neutral, speed, previous = { vx: 0, vy: 0 }, options = {}) {
  const config = { ...TILT_DEFAULTS, ...options };
  const angles = anglesFromAcceleration(sample);
  const rollDelta = angles.roll - neutral.roll;
  const forwardDelta = neutral.pitch - angles.pitch;
  const safe = angles.norm >= config.minNorm && angles.norm <= config.maxNorm;

  if (!safe) return { safe: false, vx: 0, vy: 0, ...angles };

  const rawVx = mapAngleToAxis(rollDelta, config.deadzone, config.fullScale) * speed;
  const rawVy = mapAngleToAxis(forwardDelta, config.deadzone, config.fullScale) * speed;
  const vx = previous.vx + config.alpha * (rawVx - previous.vx);
  const vy = previous.vy + config.alpha * (rawVy - previous.vy);
  return {
    safe: true,
    vx: Math.abs(vx) < 1e-12 ? 0 : vx,
    vy: Math.abs(vy) < 1e-12 ? 0 : vy,
    ...angles,
  };
}

export function isSensorFresh(sensorAt, now = Date.now(), maxAge = 300) {
  return sensorAt > 0 && now - sensorAt <= maxAge;
}

export function steeringCommand(raw, speed, limit = 0.22, expo = 2.2, deadzone = 0.08) {
  const input = clamp(Number(raw) || 0, -1, 1);
  if (Math.abs(input) <= deadzone) return 0;
  const scaled = (Math.abs(input) - deadzone) / (1 - deadzone);
  const shaped = 0.28 * scaled + 0.72 * Math.pow(scaled, expo);
  return Math.sign(input) * shaped * speed * limit;
}

export function calculateWheelGains(turns, minGain = 0.7, maxGain = 1.3) {
  if (!Array.isArray(turns) || turns.length !== 3) return null;
  const values = turns.map(Number);
  if (values.some(value => !Number.isFinite(value) || value <= 0)) return null;
  const target = Math.min(...values);
  return values.map(value => clamp(target / value, minGain, maxGain));
}

export function encodeCommand(type, sequence, x = 0, y = 0, z = 0) {
  const frame = new ArrayBuffer(12);
  const view = new DataView(frame);
  view.setUint8(0, 1);
  view.setUint8(1, type);
  view.setUint32(2, sequence >>> 0, true);
  view.setInt16(6, clamp(Math.round(x), -1000, 1000), true);
  view.setInt16(8, clamp(Math.round(y), -1000, 1000), true);
  const zLimit = type === MESSAGE_TYPES.wheelTest ? 5000 : 1000;
  view.setInt16(10, clamp(Math.round(z), -zLimit, zLimit), true);
  return frame;
}
