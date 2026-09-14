import test from 'node:test';
import assert from 'node:assert/strict';

import {
  MESSAGE_TYPES,
  SPEED_LEVELS,
  anglesFromAcceleration,
  averageNeutral,
  calculateWheelGains,
  encodeCommand,
  isSensorFresh,
  mapAngleToAxis,
  steeringCommand,
  updateTilt,
} from '../common/control.js';

const degrees = value => value * Math.PI / 180;

test('flat phone reports zero roll and pitch', () => {
  const angles = anglesFromAcceleration({ x: 0, y: 0, z: 1 });
  assert.equal(angles.roll, 0);
  assert.equal(angles.pitch, 0);
  assert.equal(angles.norm, 1);
});

test('right tilt maps to positive VX', () => {
  const angle = degrees(14);
  const result = updateTilt(
    { x: Math.sin(angle), y: 0, z: Math.cos(angle) },
    { roll: 0, pitch: 0 },
    SPEED_LEVELS.standard,
    { vx: 0, vy: 0 },
    { alpha: 1 },
  );
  assert.equal(result.safe, true);
  assert.ok(result.vx > 0);
  assert.equal(result.vy, 0);
});

test('forward tilt maps to positive VY', () => {
  const angle = degrees(14);
  const result = updateTilt(
    { x: 0, y: Math.sin(angle), z: Math.cos(angle) },
    { roll: 0, pitch: 0 },
    SPEED_LEVELS.standard,
    { vx: 0, vy: 0 },
    { alpha: 1 },
  );
  assert.equal(result.safe, true);
  assert.ok(result.vy > 0);
  assert.equal(result.vx, 0);
});

test('angle mapping has a 3 degree deadzone and reaches full scale at 25 degrees', () => {
  assert.equal(mapAngleToAxis(2.9), 0);
  assert.equal(mapAngleToAxis(-3), 0);
  assert.equal(mapAngleToAxis(25), 1);
  assert.equal(mapAngleToAxis(-25), -1);
  assert.ok(Math.abs(mapAngleToAxis(14) - 0.5) < 1e-9);
});

test('tilt output uses a 0.25 low-pass step', () => {
  const angle = degrees(25);
  const result = updateTilt(
    { x: Math.sin(angle), y: 0, z: Math.cos(angle) },
    { roll: 0, pitch: 0 },
    0.75,
    { vx: 0, vy: 0 },
  );
  assert.ok(Math.abs(result.vx - 0.1875) < 1e-9);
});

test('large tilt stays at maximum output while abnormal acceleration disables output', () => {
  const excessive = degrees(41);
  const tilted = updateTilt(
    { x: Math.sin(excessive), y: 0, z: Math.cos(excessive) },
    { roll: 0, pitch: 0 },
    0.55,
    { vx: 0.2, vy: 0.2 },
    { alpha: 1 },
  );
  const falling = updateTilt(
    { x: 0, y: 0, z: 0.2 },
    { roll: 0, pitch: 0 },
    0.55,
    { vx: 0.2, vy: 0.2 },
  );
  assert.equal(tilted.safe, true);
  assert.equal(tilted.vx, 0.55);
  assert.deepEqual({ safe: falling.safe, vx: falling.vx, vy: falling.vy }, { safe: false, vx: 0, vy: 0 });
});

test('full steering is limited to 22 percent and small steering is progressive', () => {
  assert.ok(Math.abs(steeringCommand(1, 0.55) - 0.121) < 1e-9);
  assert.equal(steeringCommand(0.05, 0.55), 0);
  assert.ok(steeringCommand(0.5, 0.55) < 0.05);
});

test('wheel calibration slows faster wheels to the slowest measured wheel', () => {
  assert.deepEqual(calculateWheelGains([10, 8, 9]), [0.8, 1, 8 / 9]);
  assert.equal(calculateWheelGains([10, 0, 9]), null);
});

test('calibration averages roll and pitch and requires five samples', () => {
  assert.equal(averageNeutral([{ roll: 1, pitch: 2 }]), null);
  const neutral = averageNeutral([
    { roll: 1, pitch: -2 },
    { roll: 2, pitch: -1 },
    { roll: 3, pitch: 0 },
    { roll: 4, pitch: 1 },
    { roll: 5, pitch: 2 },
  ]);
  assert.deepEqual(neutral, { roll: 3, pitch: 0 });
});

test('binary drive command matches MicroPython little-endian protocol', () => {
  const bytes = [...new Uint8Array(encodeCommand(MESSAGE_TYPES.drive, 42, 500, -250, 0))];
  assert.deepEqual(bytes, [1, 1, 42, 0, 0, 0, 244, 1, 6, 255, 0, 0]);
});

test('wheel test protocol preserves a five second duration', () => {
  const bytes = [...new Uint8Array(encodeCommand(MESSAGE_TYPES.wheelTest, 7, 1, 250, 5000))];
  assert.deepEqual(bytes, [1, 8, 7, 0, 0, 0, 1, 0, 250, 0, 136, 19]);
});

test('sensor data becomes stale after 300 milliseconds', () => {
  assert.equal(isSensorFresh(1000, 1300), true);
  assert.equal(isSensorFresh(1000, 1301), false);
  assert.equal(isSensorFresh(0, 100), false);
});
