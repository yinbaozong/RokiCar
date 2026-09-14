"use strict";

const assert = require("node:assert/strict");
const control = require("../app/src/main/assets/control-core.js");

function close(actual, expected, tolerance = 1e-9) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);
}

const standard = control.speedFor("standard");

close(control.speedFor("extreme"), 1);

const right = control.singleVector(1, 0, standard);
close(right.vx, standard * 0.85);
close(right.vy, 0);
close(right.rot, 0);

const forward = control.singleVector(0, 1, standard);
close(forward.vx, 0);
close(forward.vy, standard);
close(forward.rot, 0);

const diagonal = control.singleVector(1, 1, standard);
assert.ok(diagonal.vx > 0 && diagonal.vy > 0);
close(diagonal.rot, 0);
assert.ok(Math.hypot(diagonal.vx / 0.85, diagonal.vy) <= standard + 1e-9);

const leftTilt = control.tiltVector(12, 0, 0, 0, standard);
assert.ok(leftTilt.vx < 0, "positive native roll must map to a left move");
close(leftTilt.vy, 0);
close(leftTilt.rot, 0);

const forwardTilt = control.tiltVector(0, 15, 0, 0, standard);
close(forwardTilt.vx, 0);
assert.ok(forwardTilt.vy > 0, "camera-side-down tilt must map forward");

const diagonalTilt = control.tiltVector(25, 25, 0, 0, standard);
assert.ok(Math.hypot(diagonalTilt.vx, diagonalTilt.vy) <= standard + 1e-9);

close(control.shortestAngle(10, 350), 20);
close(control.shortestAngle(350, 10), -20);
close(control.headingFollowCommand(90, 0, 0, standard), standard * 0.55);
close(control.headingFollowCommand(0, 0, 0, standard), 0);
assert.ok(control.headingFollowCommand(350, 0, 0, standard) < 0);
assert.ok(control.headingFollowCommand(3, 0, 0, standard) === 0);

close(control.steeringCommand(1, standard), standard * 0.35);
close(control.steeringCommand(-1, standard), -standard * 0.35);
close(control.steeringCommand(0.05, standard), 0);

close(control.drivingSteeringCommand(-1, standard, 1), -standard * 0.35);
close(control.drivingSteeringCommand(-1, standard, -1), standard * 0.35);
close(control.drivingSteeringCommand(1, standard, -1), -standard * 0.35);
close(control.drivingSteeringCommand(1, standard, 0), standard * 0.35);

close(control.rotationCommand("slow", "hold"), 0.42);
close(control.rotationCommand("standard", "hold"), 0.50);
close(control.rotationCommand("fast", "hold"), 0.60);
close(control.rotationCommand("extreme", "hold"), 0.68);
close(control.rotationCommand("standard", "kick"), 0.70);
assert.equal(control.ROTATION_KICK_MS, 180);

const gains = control.calculateGains([10, 8, 9]);
assert.equal(gains.ok, true);
assert.deepEqual(gains.values.map(v => Number(v.toFixed(3))), [0.8, 1, 0.889]);

const outOfRange = control.calculateGains([20, 8, 9]);
assert.equal(outOfRange.ok, false);
assert.equal(outOfRange.reason, "range");

const invalid = control.calculateGains([8, 0, 9]);
assert.equal(invalid.ok, false);
assert.equal(invalid.reason, "invalid");

const strongest = control.chooseWifiDirection(-67, [
  { name: "front", vx: 0, vy: 1, rssi: -63 },
  { name: "right", vx: 1, vy: 0, rssi: -72 },
  { name: "back", vx: 0, vy: -1, rssi: -69 }
]);
assert.equal(strongest.name, "front");
assert.equal(strongest.gain, 4);
assert.equal(control.chooseWifiDirection(-67, [
  { name: "front", rssi: -66 },
  { name: "right", rssi: -68 }
]), null);
assert.equal(control.chooseWifiDirection(-67, [{ name: "bad", rssi: NaN }]), null);
assert.equal(control.shouldStopForRssi(-28), true);
assert.equal(control.shouldStopForRssi(-22), true);
assert.equal(control.shouldStopForRssi(-29), false);
assert.equal(control.shouldStopForRssi(null), false);

const gradient = control.estimateWifiGradient({ right: -50, left: -60, front: -45, back: -55 });
assert.equal(gradient.ok, true);
close(gradient.x, Math.SQRT1_2);
close(gradient.y, Math.SQRT1_2);
close(gradient.magnitude, Math.hypot(10, 10));

const weakGradient = control.estimateWifiGradient({ right: -50, left: -51, front: -49, back: -50 });
assert.equal(weakGradient.ok, false);

const badGradient = control.estimateWifiGradient({ right: NaN, left: -51, front: -49, back: -50 });
assert.equal(badGradient.ok, false);

const recorded = [
  { vx: 0, vy: 0.4, rot: 0, duration: 1000 },
  { vx: 0.2, vy: 0, rot: 0.1, duration: 500 }
];
const replay = control.invertMotionHistory(recorded, 1.25);
assert.equal(replay.length, 2);
close(replay[0].vx, -0.25);
close(replay[0].rot, -0.125);
close(replay[0].duration, 400);
close(replay[1].vy, -0.5);
close(replay[1].duration, 800);

const exactReplay = control.invertMotionHistory(recorded, 1);
close(exactReplay[0].vx, -0.2);
close(exactReplay[0].duration, 500);
close(exactReplay[1].vy, -0.4);
close(exactReplay[1].duration, 1000);

const cleanedHistory = control.sanitizeMotionHistory([
  { vx: 0, vy: 0.5, rot: 0, duration: 900 },
  { vx: NaN, vy: 0, rot: 0, duration: 300 },
  { vx: 0.2, vy: 0, rot: 0, duration: 700 }
], 1000);
assert.equal(cleanedHistory.length, 2);
close(cleanedHistory[0].duration, 300);
close(cleanedHistory[1].duration, 700);

assert.equal(control.evaluateWifiStep(-58, -55), "continue");
assert.equal(control.evaluateWifiStep(-58, -61), "rollback");
assert.equal(control.evaluateWifiStep(-58, -58), "reprobe");
assert.equal(control.evaluateWifiStep(-58, null), "stop");
assert.equal(control.homeSignalTarget(-42, -28, 6), -48);
assert.equal(control.homeSignalTarget(null, -28, 6), -28);
assert.equal(control.isHomeSignal(-47, -42, -28, 6), true);
assert.equal(control.isHomeSignal(-50, -42, -28, 6), false);

assert.equal(control.adaptiveHomeTarget(-24), -30);
assert.equal(control.adaptiveHomeTarget(-40), -42);
assert.equal(control.adaptiveHomeTarget(null), -30);

const improvingTrend = control.analyzeRssiTrend([-62, -61, -60, -58, -57]);
assert.equal(improvingTrend.direction, "improving");
const worseningTrend = control.analyzeRssiTrend([-54, -55, -56, -58, -59]);
assert.equal(worseningTrend.direction, "worsening");
const noisyTrend = control.analyzeRssiTrend([-58, -57, -59, -58, -57]);
assert.equal(noisyTrend.direction, "flat");

const voiceMove = control.normalizeVoicePlan({
  action: "move",
  direction: "forward",
  speed: "extreme",
  duration_ms: 9000,
  reply: "我往前走"
});
assert.deepEqual(voiceMove, {
  ok: true,
  action: "move",
  vx: 0,
  vy: 1,
  rot: 0,
  duration: 5000,
  reply: "我往前走"
});

const voiceDiagonal = control.normalizeVoicePlan({
  action: "move",
  direction: "left_forward",
  speed: "standard",
  duration_ms: 2000
});
assert.ok(voiceDiagonal.ok);
assert.ok(voiceDiagonal.vx < 0 && voiceDiagonal.vy > 0);
close(Math.hypot(voiceDiagonal.vx, voiceDiagonal.vy), standard);

const voiceRotate = control.normalizeVoicePlan({
  action: "rotate",
  direction: "right",
  speed: "fast",
  duration_ms: 1800
});
assert.ok(voiceRotate.ok);
close(voiceRotate.rot, 0.45);
assert.equal(voiceRotate.duration, 1800);

assert.deepEqual(control.normalizeVoicePlan({ action: "stop" }), {
  ok: true, action: "stop", vx: 0, vy: 0, rot: 0, duration: 0, reply: "已停车"
});
assert.equal(control.normalizeVoicePlan({ action: "move", direction: "up" }).ok, false);

const distance = control.estimatePathDistance([
  { vx: 0, vy: 0.5, rot: 0, duration: 2000 },
  { vx: -0.5, vy: 0, rot: 0, duration: 1000 }
], { forward: 400, backward: 380, lateral: 300 });
close(distance.forwardMm, 400);
close(distance.leftMm, 150);
close(distance.totalMm, 550);

for (const shape of ["triangle", "square", "star", "heart"]) {
  const path = control.buildShapePath(shape, "small", "standard", {
    forward: 400,
    backward: 400,
    lateral: 300
  });
  assert.equal(path.ok, true, `${shape} should build`);
  assert.ok(path.segments.length >= (shape === "heart" ? 20 : 3));
  assert.ok(path.durationMs > 0 && path.durationMs <= 60000);
  let x = 0;
  let y = 0;
  for (const segment of path.segments) {
    close(segment.rot, 0);
    x += segment.vx * segment.duration;
    y += segment.vy * segment.duration;
  }
  close(x, 0, 1e-6);
  close(y, 0, 1e-6);
}

assert.equal(control.buildShapePath("heart", "medium", "standard", {}).ok, false);

console.log("OmniControl tests passed");
