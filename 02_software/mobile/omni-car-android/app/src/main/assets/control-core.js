(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.OmniControl = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const SPEEDS = Object.freeze({ slow: 0.35, standard: 0.55, fast: 0.75, extreme: 1.0 });
  const SINGLE_X_SCALE = 0.85;
  const STEER_LIMIT = 0.35;
  const STEER_EXPO = 2.2;
  const STEER_DEADZONE = 0.08;
  const STICK_DEADZONE = 0.07;
  const ROTATION_HOLD = Object.freeze({ slow: 0.42, standard: 0.50, fast: 0.60, extreme: 0.68 });
  const ROTATION_KICK = 0.70;
  const ROTATION_KICK_MS = 180;

  function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
  }

  function speedFor(name) {
    return SPEEDS[name] || SPEEDS.standard;
  }

  function applyDeadzone(raw, deadzone, exponent) {
    const magnitude = Math.abs(clamp(raw, -1, 1));
    if (magnitude <= deadzone) return 0;
    return Math.sign(raw) * Math.pow((magnitude - deadzone) / (1 - deadzone), exponent);
  }

  function singleVector(rawX, rawY, speed) {
    let x = clamp(rawX, -1, 1);
    let y = clamp(rawY, -1, 1);
    const magnitude = Math.hypot(x, y);
    if (magnitude > 1) {
      x /= magnitude;
      y /= magnitude;
    }
    const normalizedMagnitude = Math.min(1, magnitude);
    if (normalizedMagnitude <= STICK_DEADZONE) return { vx: 0, vy: 0, rot: 0 };
    const command = speed * Math.pow(
      (normalizedMagnitude - STICK_DEADZONE) / (1 - STICK_DEADZONE),
      1.2
    );
    return {
      vx: x / normalizedMagnitude * command * SINGLE_X_SCALE,
      vy: y / normalizedMagnitude * command,
      rot: 0
    };
  }

  function tiltVector(roll, pitch, neutralRoll, neutralPitch, speed) {
    const map = angle => {
      const magnitude = Math.abs(angle);
      if (magnitude <= 3) return 0;
      return Math.sign(angle) * clamp((magnitude - 3) / 22, 0, 1);
    };
    let x = map((neutralRoll || 0) - roll);
    let y = map(pitch - (neutralPitch || 0));
    const magnitude = Math.hypot(x, y);
    if (magnitude > 1) {
      x /= magnitude;
      y /= magnitude;
    }
    return { vx: x * speed, vy: y * speed, rot: 0 };
  }

  function shortestAngle(target, current) {
    return ((Number(target) - Number(current) + 540) % 360) - 180;
  }

  function headingFollowCommand(phoneHeading, neutralHeading, carYaw, speed) {
    const targetYaw = shortestAngle(phoneHeading, neutralHeading);
    const error = shortestAngle(targetYaw, carYaw);
    if (Math.abs(error) <= 4) return 0;
    return Math.sign(error) * clamp((Math.abs(error) - 4) / 41, 0, 1) * speed * 0.55;
  }

  function steeringCommand(raw, speed) {
    const magnitude = Math.abs(clamp(raw, -1, 1));
    if (magnitude <= STEER_DEADZONE) return 0;
    const t = (magnitude - STEER_DEADZONE) / (1 - STEER_DEADZONE);
    const shaped = 0.28 * t + 0.72 * Math.pow(t, STEER_EXPO);
    return Math.sign(raw) * shaped * speed * STEER_LIMIT;
  }

  function drivingSteeringCommand(raw, speed, throttle) {
    const command = steeringCommand(raw, speed);
    return throttle < 0 ? -command : command;
  }

  function chooseWifiDirection(baseline, samples, minimumGain) {
    const threshold = Number.isFinite(minimumGain) ? minimumGain : 2;
    if (!Number.isFinite(baseline) || !Array.isArray(samples)) return null;
    const valid = samples.filter(sample => sample && Number.isFinite(sample.rssi));
    if (!valid.length) return null;
    const best = valid.reduce((winner, sample) => sample.rssi > winner.rssi ? sample : winner);
    const gain = best.rssi - baseline;
    return gain >= threshold ? Object.assign({}, best, { gain }) : null;
  }

  function shouldStopForRssi(rssi, threshold) {
    const target = Number.isFinite(threshold) ? threshold : -28;
    return Number.isFinite(rssi) && rssi >= target;
  }

  function estimateWifiGradient(samples, minimumMagnitude) {
    const required = ["right", "left", "front", "back"];
    if (!samples || required.some(key => !Number.isFinite(samples[key]))) {
      return { ok: false, x: 0, y: 0, magnitude: 0 };
    }
    const dx = samples.right - samples.left;
    const dy = samples.front - samples.back;
    const magnitude = Math.hypot(dx, dy);
    const threshold = Number.isFinite(minimumMagnitude) ? minimumMagnitude : 3;
    if (magnitude < threshold) return { ok: false, x: 0, y: 0, magnitude };
    return { ok: true, x: dx / magnitude, y: dy / magnitude, magnitude, dx, dy };
  }

  function invertMotionHistory(history, requestedSpeedup) {
    if (!Array.isArray(history) || !history.length) return [];
    const valid = history.filter(item => item && Number.isFinite(item.vx) && Number.isFinite(item.vy) &&
      Number.isFinite(item.rot) && Number.isFinite(item.duration) && item.duration > 0);
    if (!valid.length) return [];
    const maxCommand = valid.reduce((maximum, item) => Math.max(maximum,
      Math.abs(item.vx), Math.abs(item.vy), Math.abs(item.rot)), 0);
    const requested = Number.isFinite(requestedSpeedup) ? Math.max(1, requestedSpeedup) : 1.25;
    const speedup = maxCommand > 0 ? Math.min(requested, 1 / maxCommand) : 1;
    return valid.slice().reverse().map(item => ({
      vx: -item.vx * speedup,
      vy: -item.vy * speedup,
      rot: -item.rot * speedup,
      duration: item.duration / speedup
    }));
  }

  function sanitizeMotionHistory(history, maximumDuration) {
    if (!Array.isArray(history)) return [];
    const limit = Number.isFinite(maximumDuration) ? Math.max(0, maximumDuration) : 600000;
    const valid = history.filter(item => item && Number.isFinite(item.vx) &&
      Number.isFinite(item.vy) && Number.isFinite(item.rot) &&
      Number.isFinite(item.duration) && item.duration > 0);
    const result = [];
    let remaining = limit;
    for (let index = valid.length - 1; index >= 0 && remaining > 0; index--) {
      const item = valid[index];
      const duration = Math.min(item.duration, remaining);
      result.unshift({
        vx: clamp(item.vx, -1, 1),
        vy: clamp(item.vy, -1, 1),
        rot: clamp(item.rot, -1, 1),
        duration
      });
      remaining -= duration;
    }
    return result;
  }

  function evaluateWifiStep(reference, current, improvementThreshold, dropThreshold) {
    if (!Number.isFinite(reference) || !Number.isFinite(current)) return "stop";
    const improve = Number.isFinite(improvementThreshold) ? improvementThreshold : 1;
    const drop = Number.isFinite(dropThreshold) ? dropThreshold : 2;
    const delta = current - reference;
    if (delta >= improve) return "continue";
    if (delta <= -drop) return "rollback";
    return "reprobe";
  }

  function homeSignalTarget(homeRssi, fallback, tolerance) {
    const defaultTarget = Number.isFinite(fallback) ? fallback : -28;
    const margin = Number.isFinite(tolerance) ? Math.max(0, tolerance) : 6;
    return Number.isFinite(homeRssi) ? homeRssi - margin : defaultTarget;
  }

  function isHomeSignal(currentRssi, homeRssi, fallback, tolerance) {
    return Number.isFinite(currentRssi) &&
      currentRssi >= homeSignalTarget(homeRssi, fallback, tolerance);
  }

  function adaptiveHomeTarget(homeRssi, fixedTarget, tolerance) {
    const fixed = Number.isFinite(fixedTarget) ? fixedTarget : -30;
    const margin = Number.isFinite(tolerance) ? Math.max(0, tolerance) : 2;
    return Number.isFinite(homeRssi) ? Math.min(fixed, homeRssi - margin) : fixed;
  }

  function median(values) {
    const sorted = values.filter(Number.isFinite).slice().sort((a, b) => a - b);
    if (!sorted.length) return null;
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
  }

  function analyzeRssiTrend(samples, threshold) {
    const values = Array.isArray(samples) ? samples.filter(Number.isFinite) : [];
    if (values.length < 4) return { direction: "unknown", delta: 0, current: median(values) };
    const width = Math.max(2, Math.floor(values.length / 2));
    const before = median(values.slice(0, width));
    const after = median(values.slice(-width));
    const delta = after - before;
    const minimum = Number.isFinite(threshold) ? Math.max(0, threshold) : 2;
    return {
      direction: delta >= minimum ? "improving" : delta <= -minimum ? "worsening" : "flat",
      delta,
      current: after
    };
  }

  function shapePoints(shape) {
    if (shape === "triangle") return [[0, -0.5], [0.5, 0.5], [-0.5, 0.5], [0, -0.5]];
    if (shape === "square") return [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5], [-0.5, -0.5]];
    if (shape === "star") {
      const points = [];
      for (let index = 0; index < 10; index++) {
        const radius = index % 2 ? 0.22 : 0.5;
        const angle = -Math.PI / 2 + index * Math.PI / 5;
        points.push([Math.cos(angle) * radius, Math.sin(angle) * radius]);
      }
      points.push(points[0].slice());
      return points;
    }
    if (shape === "heart") {
      const raw = [];
      for (let index = 0; index < 24; index++) {
        const angle = index * Math.PI * 2 / 24;
        const x = 16 * Math.pow(Math.sin(angle), 3);
        const y = -(13 * Math.cos(angle) - 5 * Math.cos(2 * angle) -
          2 * Math.cos(3 * angle) - Math.cos(4 * angle));
        raw.push([x, y]);
      }
      const xs = raw.map(point => point[0]);
      const ys = raw.map(point => point[1]);
      const width = Math.max(...xs) - Math.min(...xs);
      const height = Math.max(...ys) - Math.min(...ys);
      const scale = 1 / Math.max(width, height);
      const centerX = (Math.max(...xs) + Math.min(...xs)) / 2;
      const centerY = (Math.max(...ys) + Math.min(...ys)) / 2;
      const points = raw.map(point => [(point[0] - centerX) * scale, (point[1] - centerY) * scale]);
      points.push(points[0].slice());
      return points;
    }
    return null;
  }

  function buildShapePath(shape, sizeName, speedName, calibration) {
    const points = shapePoints(shape);
    const rates = calibration || {};
    const lateral = Number(rates.lateral);
    const forward = Number(rates.forward);
    const backward = Number(rates.backward);
    if (!points || !(lateral > 0) || !(forward > 0) || !(backward > 0)) {
      return { ok: false, reason: points ? "calibration" : "shape", segments: [] };
    }
    const sizes = { small: 300, medium: 500, large: 800 };
    const sizeMm = sizes[sizeName] || sizes.medium;
    const speed = speedFor(speedName);
    const segments = [];
    let durationMs = 0;
    for (let index = 1; index < points.length; index++) {
      const dx = (points[index][0] - points[index - 1][0]) * sizeMm;
      const dy = (points[index][1] - points[index - 1][1]) * sizeMm;
      const xSeconds = dx / lateral;
      const ySeconds = dy / (dy >= 0 ? forward : backward);
      const seconds = Math.hypot(xSeconds, ySeconds) / speed;
      if (!(seconds > 0)) continue;
      const duration = seconds * 1000;
      segments.push({
        vx: xSeconds / seconds,
        vy: ySeconds / seconds,
        rot: 0,
        duration
      });
      durationMs += duration;
    }
    if (!segments.length || durationMs > 60000) return { ok: false, reason: "duration", segments: [] };
    return { ok: true, shape, size: sizeName, sizeMm, points, segments, durationMs };
  }

  function rotationCommand(speedName, phase) {
    return phase === "kick" ? ROTATION_KICK : ROTATION_HOLD[speedName] || ROTATION_HOLD.standard;
  }

  function calculateGains(turns) {
    if (!Array.isArray(turns) || turns.length !== 3 || turns.some(v => !Number.isFinite(v) || v <= 0)) {
      return { ok: false, reason: "invalid", values: null, target: null };
    }
    const target = Math.min(...turns);
    const rawValues = turns.map(value => target / value);
    if (rawValues.some(value => value < 0.70)) {
      return { ok: false, reason: "range", values: rawValues, target };
    }
    return { ok: true, reason: null, values: rawValues, target };
  }

  function normalizeVoicePlan(raw) {
    const plan = raw && typeof raw === "object" ? raw : {};
    const action = String(plan.action || "").toLowerCase();
    const reply = typeof plan.reply === "string" && plan.reply.trim()
      ? plan.reply.trim().slice(0, 80)
      : action === "stop" ? "已停车" : "";
    if (action === "stop") {
      return { ok: true, action, vx: 0, vy: 0, rot: 0, duration: 0, reply };
    }
    if (action === "return_home" || action === "go_out" || action === "chat") {
      return { ok: true, action, vx: 0, vy: 0, rot: 0, duration: 0, reply };
    }
    if (action === "draw_shape") {
      const shape = String(plan.shape || "").toLowerCase();
      const size = String(plan.size || "medium").toLowerCase();
      if (!["heart", "triangle", "square", "star"].includes(shape) ||
          !["small", "medium", "large"].includes(size)) return { ok: false, reason: "shape" };
      return { ok: true, action, shape, size, speed: String(plan.speed || "standard"),
        vx: 0, vy: 0, rot: 0, duration: 0, reply };
    }
    const duration = Math.round(clamp(Number(plan.duration_ms) || 2000, 200, 5000));
    const speed = speedFor(String(plan.speed || "standard"));
    if (action === "rotate") {
      const sign = plan.direction === "left" ? -1 : plan.direction === "right" ? 1 : 0;
      if (!sign) return { ok: false, reason: "direction" };
      return { ok: true, action, vx: 0, vy: 0, rot: sign * speed * 0.6, duration, reply };
    }
    if (action !== "move") return { ok: false, reason: "action" };
    const directions = {
      forward: [0, 1], backward: [0, -1], left: [-1, 0], right: [1, 0],
      left_forward: [-1, 1], right_forward: [1, 1],
      left_backward: [-1, -1], right_backward: [1, -1]
    };
    const vector = directions[plan.direction];
    if (!vector) return { ok: false, reason: "direction" };
    const length = Math.hypot(vector[0], vector[1]);
    return {
      ok: true,
      action,
      vx: vector[0] / length * speed,
      vy: vector[1] / length * speed,
      rot: 0,
      duration,
      reply
    };
  }

  function estimatePathDistance(history, calibration) {
    const rates = calibration || {};
    const result = { forwardMm: 0, backwardMm: 0, leftMm: 0, rightMm: 0, totalMm: 0 };
    if (!Array.isArray(history)) return result;
    history.forEach(item => {
      if (!item || !Number.isFinite(item.duration)) return;
      const seconds = Math.max(0, item.duration) / 1000;
      const x = Number(item.vx) || 0;
      const y = Number(item.vy) || 0;
      const yDistance = Math.abs(y) * seconds * (y >= 0 ? Number(rates.forward) || 0 : Number(rates.backward) || 0);
      const xDistance = Math.abs(x) * seconds * (Number(rates.lateral) || 0);
      if (y >= 0) result.forwardMm += yDistance; else result.backwardMm += yDistance;
      if (x >= 0) result.rightMm += xDistance; else result.leftMm += xDistance;
      result.totalMm += Math.hypot(xDistance, yDistance);
    });
    return result;
  }

  return Object.freeze({
    SPEEDS,
    SINGLE_X_SCALE,
    STEER_LIMIT,
    ROTATION_HOLD,
    ROTATION_KICK,
    ROTATION_KICK_MS,
    clamp,
    speedFor,
    applyDeadzone,
    singleVector,
    tiltVector,
    shortestAngle,
    headingFollowCommand,
    steeringCommand,
    drivingSteeringCommand,
    chooseWifiDirection,
    shouldStopForRssi,
    estimateWifiGradient,
    invertMotionHistory,
    sanitizeMotionHistory,
    evaluateWifiStep,
    homeSignalTarget,
    isHomeSignal,
    adaptiveHomeTarget,
    analyzeRssiTrend,
    buildShapePath,
    rotationCommand,
    calculateGains,
    normalizeVoicePlan,
    estimatePathDistance
  });
});
