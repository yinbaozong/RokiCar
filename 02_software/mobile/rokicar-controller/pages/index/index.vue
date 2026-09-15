<template>
  <view class="page">
    <view class="topbar">
      <text class="brand">RokiCar</text>
      <text class="connection" :class="connectionClass">{{ connectionText }}</text>
    </view>

    <view class="control-surface">
      <view class="toolbar-row">
        <text class="toolbar-label">模式</text>
        <view class="segments modes">
          <button v-for="item in modes" :key="item.id" class="segment" :class="{ selected: mode === item.id }" @tap="selectMode(item.id)">{{ item.label }}</button>
        </view>
      </view>
      <view class="toolbar-row">
        <text class="toolbar-label">速度</text>
        <view class="segments speeds">
          <button v-for="item in speeds" :key="item.id" class="segment" :class="{ selected: speedName === item.id }" @tap="selectSpeed(item.id)">{{ item.label }}</button>
        </view>
      </view>

      <view class="front"><text>车头</text><text class="front-arrow">↑</text></view>

      <view v-show="mode === 'dpad'" class="panel dpad-panel">
        <view class="dpad">
          <button class="drive-key forward" aria-label="前进" @touchstart.stop.prevent="pressDirection('forward')" @touchend.stop.prevent="releaseDirection" @touchcancel.stop.prevent="releaseDirection">↑</button>
          <button class="drive-key left" aria-label="左移" @touchstart.stop.prevent="pressDirection('left')" @touchend.stop.prevent="releaseDirection" @touchcancel.stop.prevent="releaseDirection">←</button>
          <button class="drive-key center-stop" aria-label="停止" @tap="stopAll">■</button>
          <button class="drive-key right" aria-label="右移" @touchstart.stop.prevent="pressDirection('right')" @touchend.stop.prevent="releaseDirection" @touchcancel.stop.prevent="releaseDirection">→</button>
          <button class="drive-key back" aria-label="后退" @touchstart.stop.prevent="pressDirection('back')" @touchend.stop.prevent="releaseDirection" @touchcancel.stop.prevent="releaseDirection">↓</button>
        </view>
      </view>

      <view v-show="mode === 'single'" class="panel">
        <view id="app-single-stick" class="stick single-stick" @touchstart.stop.prevent="startStick('single', $event)" @touchmove.stop.prevent="moveStick('single', $event)" @touchend.stop.prevent="endStick('single')" @touchcancel.stop.prevent="endStick('single')">
          <view class="cross vertical"></view><view class="cross horizontal"></view>
          <view class="knob" :style="knobStyle('single')"></view>
        </view>
      </view>

      <view v-show="mode === 'dual'" class="panel dual-panel">
        <view class="dual-grid">
          <view class="dual-unit">
            <view id="app-move-stick" class="stick dual-stick" @touchstart.stop.prevent="startStick('move', $event)" @touchmove.stop.prevent="moveStick('move', $event)" @touchend.stop.prevent="endStick('move')" @touchcancel.stop.prevent="endStick('move')">
              <view class="cross vertical"></view><view class="cross horizontal"></view>
              <view class="knob small" :style="knobStyle('move')"></view>
            </view>
            <text>平移</text>
          </view>
          <view class="dual-unit">
            <view id="app-rotate-stick" class="stick dual-stick" @touchstart.stop.prevent="startStick('rotate', $event)" @touchmove.stop.prevent="moveStick('rotate', $event)" @touchend.stop.prevent="endStick('rotate')" @touchcancel.stop.prevent="endStick('rotate')">
              <view class="cross horizontal"></view>
              <view class="knob small" :style="knobStyle('rotate')"></view>
            </view>
            <text>旋转</text>
          </view>
        </view>
      </view>

      <view v-show="mode === 'tilt'" class="panel tilt-panel">
        <view class="tilt-stage" :class="{ armed: tiltArmed, calibrating: tiltCalibrating }">
          <view class="tilt-axis x-axis"></view><view class="tilt-axis y-axis"></view>
          <view class="tilt-dot" :style="tiltDotStyle"></view>
        </view>
        <view class="tilt-readout"><text>横滚 {{ tiltAngles.roll.toFixed(1) }}°</text><text>俯仰 {{ tiltAngles.pitch.toFixed(1) }}°</text></view>
        <view class="tilt-actions">
          <button class="tilt-toggle" :class="{ armed: tiltArmed || tiltCalibrating }" @tap="toggleTilt">{{ tiltButtonText }}</button>
          <button class="calibrate-button" :disabled="tiltCalibrating" @tap="recalibrateTilt">校准水平</button>
        </view>
      </view>

      <view v-if="mode !== 'dual'" class="rotation-row">
        <button class="rotate-key" aria-label="原地左转" @touchstart.stop.prevent="pressRotation(-1)" @touchend.stop.prevent="releaseRotation" @touchcancel.stop.prevent="releaseRotation">↺</button>
        <button class="rotate-key" aria-label="原地右转" @touchstart.stop.prevent="pressRotation(1)" @touchend.stop.prevent="releaseRotation" @touchcancel.stop.prevent="releaseRotation">↻</button>
      </view>

      <view class="metrics"><text>VX {{ drive.vx.toFixed(2) }}</text><text>VY {{ drive.vy.toFixed(2) }}</text><text>ROT {{ drive.rot.toFixed(2) }}</text></view>
      <button class="stop" @tap="stopAll">■ 停止</button>
    </view>

    <view class="tools">
      <button class="tool-button" @tap="runSquare">运行 20 cm 正方形</button>
      <button class="tool-button" @tap="reconnect">重新连接</button>
    </view>

    <view class="calibration">
      <text class="section-title">轮速校准</text>
      <view v-for="(gain, index) in gains" :key="index" class="gain-row">
        <text>{{ index === 2 ? 'W3' : `M${index + 1}` }}</text>
        <slider class="gain-slider" :value="gain" min="70" max="130" step="1" activeColor="#138653" backgroundColor="#d8dfda" block-size="20" @changing="changeGain(index, $event)" @change="changeGain(index, $event)" />
        <text>{{ (gain / 100).toFixed(2) }}</text>
      </view>
      <view class="cal-actions"><button @tap="applyGains">应用</button><button @tap="saveGains">保存校准</button></view>
    </view>

    <text class="status">{{ statusText }}</text>
  </view>
</template>

<script>
import {
  MESSAGE_TYPES,
  SPEED_LEVELS,
  anglesFromAcceleration,
  averageNeutral,
  encodeCommand,
  isSensorFresh,
  updateTilt,
} from '../../common/control.js';

const DIRECTIONS = { forward: [0, 1], back: [0, -1], left: [-1, 0], right: [1, 0] };
const SOCKET_URL = 'ws://192.168.4.1/ws';
const HEALTH_URL = 'http://192.168.4.1/health';

export default {
  data() {
    return {
      modes: [
        { id: 'dpad', label: '方向键' },
        { id: 'single', label: '单摇杆' },
        { id: 'dual', label: '双摇杆' },
        { id: 'tilt', label: '手机倾斜' },
      ],
      speeds: [
        { id: 'slow', label: '慢速' },
        { id: 'standard', label: '标准' },
        { id: 'fast', label: '快速' },
      ],
      mode: 'dpad',
      speedName: 'standard',
      connectionState: 'connecting',
      statusText: '请先连接 WiFi：RokiCar',
      socketTask: null,
      socketOpen: false,
      sequence: 0,
      drive: { vx: 0, vy: 0, rot: 0 },
      active: { direction: false, translate: false, rotation: false },
      knobs: { single: { x: 0, y: 0 }, move: { x: 0, y: 0 }, rotate: { x: 0, y: 0 } },
      rects: { single: null, move: null, rotate: null },
      squareActive: false,
      gains: [100, 100, 100],
      tiltArmed: false,
      tiltCalibrating: false,
      tiltNeutral: { roll: 0, pitch: 0 },
      tiltAngles: { roll: 0, pitch: 0, norm: 1 },
      tiltSamples: [],
      sensorAt: 0,
      pageVisible: false,
      ready: false,
    };
  },
  computed: {
    connectionText() {
      return { connecting: '连接中', connected: '已连接', disconnected: '未连接', error: '连接错误' }[this.connectionState];
    },
    connectionClass() { return this.connectionState === 'connected' ? 'ok' : 'warn'; },
    tiltButtonText() {
      if (this.tiltCalibrating) return '正在校准';
      return this.tiltArmed ? '关闭倾斜' : '启动倾斜';
    },
    tiltDotStyle() {
      const speed = SPEED_LEVELS[this.speedName] || 0.55;
      const x = speed ? this.drive.vx / speed * 72 : 0;
      const y = speed ? -this.drive.vy / speed * 72 : 0;
      return `transform: translate(calc(-50% + ${x}rpx), calc(-50% + ${y}rpx));`;
    },
  },
  onLoad() {
    this.mode = this.readChoice('rokicar-mode', ['dpad', 'single', 'dual', 'tilt'], 'dpad');
    this.speedName = this.readChoice('rokicar-speed', Object.keys(SPEED_LEVELS), 'standard');
    this.accelListener = sample => this.onAcceleration(sample);
    this.appHideListener = () => this.leaveForeground();
    this.appShowListener = () => this.enterForeground();
    uni.$on('rokicar-app-hide', this.appHideListener);
    uni.$on('rokicar-app-show', this.appShowListener);
  },
  onReady() {
    this.ready = true;
    this.pageVisible = true;
    this.startTimers();
    this.measureSticks();
    this.loadHealthThenConnect();
  },
  onShow() {
    this.pageVisible = true;
    if (this.ready && !this.socketOpen) this.connect();
  },
  onHide() { this.leaveForeground(); },
  onUnload() {
    this.leaveForeground();
    clearInterval(this.commandTimer);
    clearTimeout(this.reconnectTimer);
    clearTimeout(this.calibrationTimer);
    uni.$off('rokicar-app-hide', this.appHideListener);
    uni.$off('rokicar-app-show', this.appShowListener);
  },
  methods: {
    readChoice(key, allowed, fallback) {
      try { const value = uni.getStorageSync(key); return allowed.includes(value) ? value : fallback; } catch (_) { return fallback; }
    },
    saveChoice(key, value) { try { uni.setStorageSync(key, value); } catch (_) {} },
    speedLimit() { return SPEED_LEVELS[this.speedName] || SPEED_LEVELS.standard; },
    isManualActive() { return this.active.direction || this.active.translate || this.active.rotation; },
    setDrive(vx, vy, rot = this.drive.rot) { this.drive.vx = vx; this.drive.vy = vy; this.drive.rot = rot; },
    resetKnobs() {
      Object.keys(this.knobs).forEach(key => { this.knobs[key].x = 0; this.knobs[key].y = 0; });
    },
    knobStyle(name) { return `transform: translate(calc(-50% + ${this.knobs[name].x}px), calc(-50% + ${this.knobs[name].y}px));`; },
    startTimers() {
      clearInterval(this.commandTimer);
      this.lastIdlePing = 0;
      this.commandTimer = setInterval(() => {
        const now = Date.now();
        if (this.tiltArmed && !isSensorFresh(this.sensorAt, now)) { this.disarmTilt('传感器数据超时，已停车'); return; }
        if (this.tiltArmed || this.isManualActive()) this.sendDrive();
        else if (this.squareActive) this.sendCommand(MESSAGE_TYPES.ping);
        else if (now - this.lastIdlePing >= 1000) { this.sendCommand(MESSAGE_TYPES.ping); this.lastIdlePing = now; }
      }, 100);
    },
    loadHealthThenConnect() {
      uni.request({
        url: HEALTH_URL,
        method: 'GET',
        timeout: 1500,
        success: response => {
          const values = response?.data?.g;
          if (Array.isArray(values) && values.length === 3) this.gains = values.map(value => Math.round(value / 10));
        },
        complete: () => this.connect(),
      });
    },
    connect() {
      if (!this.pageVisible || this.socketOpen || this.connecting) return;
      this.connecting = true; this.connectionState = 'connecting';
      const task = uni.connectSocket({ url: SOCKET_URL, complete: () => {} });
      this.socketTask = task;
      task.onOpen(() => {
        if (this.socketTask !== task) { try { task.close({}); } catch (_) {} return; }
        this.connecting = false; this.socketOpen = true; this.connectionState = 'connected'; this.reconnectDelay = 250;
        this.statusText = '实时控制链路已连接';
      });
      task.onClose(() => {
        if (this.socketTask !== task) return;
        this.connecting = false; this.socketOpen = false; this.socketTask = null; this.shutdownMotion(false);
        this.connectionState = 'disconnected';
        if (this.pageVisible) this.scheduleReconnect();
      });
      task.onError(() => {
        if (this.socketTask !== task) return;
        this.socketTask = null; this.connecting = false; this.socketOpen = false; this.connectionState = 'error';
        this.shutdownMotion(false);
        try { task.close({}); } catch (_) {}
        this.scheduleReconnect();
      });
    },
    scheduleReconnect() {
      clearTimeout(this.reconnectTimer);
      const delay = this.reconnectDelay || 250;
      this.reconnectTimer = setTimeout(() => this.connect(), delay);
      this.reconnectDelay = Math.min(2000, delay * 2);
    },
    reconnect() {
      this.shutdownMotion(true);
      clearTimeout(this.reconnectTimer);
      const previousTask = this.socketTask;
      this.socketTask = null; this.socketOpen = false; this.connecting = false;
      if (previousTask) { try { previousTask.close({}); } catch (_) {} }
      setTimeout(() => this.connect(), 220);
    },
    sendCommand(type, x = 0, y = 0, z = 0) {
      if (!this.socketOpen || !this.socketTask) return false;
      const data = encodeCommand(type, ++this.sequence, x, y, z);
      const task = this.socketTask;
      task.send({ data, fail: () => {
        if (this.socketTask !== task) return;
        this.socketTask = null; this.socketOpen = false; this.connecting = false; this.connectionState = 'error';
        this.shutdownMotion(false);
        try { task.close({}); } catch (_) {}
        if (this.pageVisible) this.scheduleReconnect();
      } });
      return true;
    },
    sendDrive() { this.sendCommand(MESSAGE_TYPES.drive, this.drive.vx * 1000, this.drive.vy * 1000, this.drive.rot * 1000); },
    sendStop() { this.sendCommand(MESSAGE_TYPES.stop); },
    shutdownMotion(sendStop = true) {
      this.active.direction = this.active.translate = this.active.rotation = false;
      this.squareActive = false; this.setDrive(0, 0, 0); this.resetKnobs();
      this.stopTiltSensor(); this.tiltArmed = false; this.tiltCalibrating = false;
      if (sendStop) this.sendStop();
    },
    stopAll() { this.shutdownMotion(true); this.statusText = this.socketOpen ? '已停车' : '未连接，控制已清零'; },
    selectMode(nextMode) {
      if (!this.modes.some(item => item.id === nextMode) || nextMode === this.mode) return;
      this.shutdownMotion(true); this.mode = nextMode; this.saveChoice('rokicar-mode', nextMode);
      this.$nextTick(() => this.measureSticks());
    },
    selectSpeed(nextSpeed) {
      if (!(nextSpeed in SPEED_LEVELS) || nextSpeed === this.speedName) return;
      this.shutdownMotion(true); this.speedName = nextSpeed; this.saveChoice('rokicar-speed', nextSpeed);
      this.statusText = '速度已切换，请重新启用控制';
    },
    pressDirection(direction) {
      if (this.mode !== 'dpad') return;
      this.squareActive = false; this.active.direction = true;
      const vector = DIRECTIONS[direction], speed = this.speedLimit();
      this.setDrive(vector[0] * speed, vector[1] * speed); this.sendDrive();
    },
    releaseDirection() {
      this.active.direction = false; this.drive.vx = this.drive.vy = 0;
      if (this.isManualActive()) this.sendDrive(); else this.sendStop();
    },
    pressRotation(sign) {
      if (this.mode === 'tilt' && !this.tiltArmed) return;
      this.squareActive = false; this.active.rotation = true; this.drive.rot = sign * this.speedLimit(); this.sendDrive();
    },
    releaseRotation() {
      this.active.rotation = false; this.drive.rot = 0;
      if (this.tiltArmed || this.isManualActive()) this.sendDrive(); else this.sendStop();
    },
    measureSticks() {
      const selectors = { single: '#app-single-stick', move: '#app-move-stick', rotate: '#app-rotate-stick' };
      Object.keys(selectors).forEach(key => {
        uni.createSelectorQuery().in(this).select(selectors[key]).boundingClientRect(rect => { if (rect && rect.width) this.rects[key] = rect; }).exec();
      });
    },
    touchPoint(event) { return event.touches?.[0] || event.changedTouches?.[0] || null; },
    startStick(name, event) {
      this.squareActive = false;
      if (name === 'rotate') this.active.rotation = true; else this.active.translate = true;
      this.updateStick(name, event); this.sendDrive();
    },
    moveStick(name, event) { this.updateStick(name, event); },
    endStick(name) {
      this.knobs[name].x = this.knobs[name].y = 0;
      if (name === 'rotate') { this.active.rotation = false; this.drive.rot = 0; }
      else { this.active.translate = false; this.drive.vx = this.drive.vy = 0; }
      if (this.isManualActive()) this.sendDrive(); else this.sendStop();
    },
    updateStick(name, event) {
      const touch = this.touchPoint(event), rect = this.rects[name];
      if (!touch || !rect) { this.measureSticks(); return; }
      const limit = rect.width * 0.33;
      let dx = touch.clientX - rect.left - rect.width / 2;
      let dy = touch.clientY - rect.top - rect.height / 2;
      if (name === 'rotate') dy = 0;
      const distance = Math.hypot(dx, dy);
      if (distance > limit) { dx = dx / distance * limit; dy = dy / distance * limit; }
      this.knobs[name].x = dx; this.knobs[name].y = dy;
      if (name === 'rotate') {
        const raw = Math.max(-1, Math.min(1, dx / limit));
        this.drive.rot = Math.abs(raw) < 0.07 ? 0 : Math.sign(raw) * this.speedLimit() * Math.pow((Math.abs(raw) - 0.07) / 0.93, 1.2);
        return;
      }
      const rawX = Math.max(-1, Math.min(1, dx / limit));
      const rawY = Math.max(-1, Math.min(1, -dy / limit));
      const magnitude = Math.hypot(rawX, rawY);
      if (magnitude < 0.07) { this.drive.vx = this.drive.vy = 0; return; }
      const command = this.speedLimit() * (0.24 + 0.76 * Math.pow((magnitude - 0.07) / 0.93, 1.2));
      this.drive.vx = rawX / magnitude * command; this.drive.vy = rawY / magnitude * command;
    },
    toggleTilt() { if (this.tiltArmed || this.tiltCalibrating) this.disarmTilt('倾斜控制已关闭'); else this.beginTiltCalibration(); },
    recalibrateTilt() {
      if (this.mode !== 'tilt') return;
      this.disarmTilt('', true); this.beginTiltCalibration();
    },
    beginTiltCalibration() {
      if (this.mode !== 'tilt') return;
      if (!this.socketOpen) { this.statusText = '请先连接 RokiCar WiFi'; return; }
      this.shutdownMotion(true); this.tiltCalibrating = true; this.tiltSamples = []; this.sensorAt = 0;
      this.calibrationStartedAt = Date.now(); this.statusText = '保持当前握姿，正在校准水平';
      uni.setKeepScreenOn({ keepScreenOn: true });
      if (uni.onAccelerometerChange) uni.onAccelerometerChange(this.accelListener);
      uni.startAccelerometer({
        interval: 'game',
        success: () => { this.calibrationTimer = setTimeout(() => this.finishTiltCalibration(), 500); },
        fail: () => this.disarmTilt('无法读取手机加速度计'),
      });
    },
    finishTiltCalibration() {
      const neutral = averageNeutral(this.tiltSamples);
      if (!neutral && Date.now() - this.calibrationStartedAt < 1100) { this.calibrationTimer = setTimeout(() => this.finishTiltCalibration(), 500); return; }
      if (!neutral) { this.disarmTilt('姿态数据不足，校准失败'); return; }
      this.tiltNeutral = neutral; this.tiltCalibrating = false; this.tiltArmed = true; this.statusText = '倾斜控制已启动';
    },
    onAcceleration(sample) {
      const angles = anglesFromAcceleration(sample); this.tiltAngles = angles; this.sensorAt = Date.now();
      if (this.tiltCalibrating) {
        if (angles.norm >= 0.65 && angles.norm <= 1.35) this.tiltSamples.push(angles);
        return;
      }
      if (!this.tiltArmed) return;
      const result = updateTilt(sample, this.tiltNeutral, this.speedLimit(), this.drive);
      if (!result.safe) { this.disarmTilt('姿态或加速度异常，已停车'); return; }
      this.drive.vx = result.vx; this.drive.vy = result.vy; this.tiltAngles = result;
    },
    stopTiltSensor() {
      clearTimeout(this.calibrationTimer);
      try { if (uni.offAccelerometerChange) uni.offAccelerometerChange(this.accelListener); } catch (_) {}
      try { uni.stopAccelerometer({}); } catch (_) {}
      try { uni.setKeepScreenOn({ keepScreenOn: false }); } catch (_) {}
    },
    disarmTilt(message, sendStop = true) {
      this.stopTiltSensor(); this.tiltArmed = false; this.tiltCalibrating = false; this.tiltSamples = [];
      this.drive.vx = this.drive.vy = this.drive.rot = 0; this.active.rotation = false;
      if (sendStop) this.sendStop();
      if (message) this.statusText = message;
    },
    runSquare() {
      this.shutdownMotion(true); this.squareActive = true;
      if (!this.sendCommand(MESSAGE_TYPES.square, 200, 550, 0)) { this.squareActive = false; this.statusText = '未连接，无法运行测试'; }
      else this.statusText = '正在运行 20 cm 正方形';
    },
    changeGain(index, event) { this.$set(this.gains, index, Number(event.detail.value)); },
    applyGains() { this.shutdownMotion(true); this.sendCommand(MESSAGE_TYPES.gains, ...this.gains.map(value => value * 10)); this.statusText = '校准值已应用'; },
    saveGains() { this.applyGains(); setTimeout(() => this.sendCommand(MESSAGE_TYPES.save), 80); this.statusText = '校准值已保存到小车'; },
    enterForeground() { this.pageVisible = true; if (this.ready && !this.socketOpen) this.connect(); },
    leaveForeground() {
      this.pageVisible = false; this.shutdownMotion(true); clearTimeout(this.reconnectTimer);
      const previousTask = this.socketTask;
      this.socketTask = null; this.socketOpen = false; this.connecting = false; this.connectionState = 'disconnected';
      if (previousTask) { try { previousTask.close({}); } catch (_) {} }
    },
  },
};
</script>

<style scoped>
.page { min-height: 100vh; padding: calc(24rpx + var(--status-bar-height)) 24rpx calc(54rpx + env(safe-area-inset-bottom)); background: #f4f6f3; color: #152019; font-family: Arial, "Microsoft YaHei", sans-serif; }
.topbar { min-height: 82rpx; display: flex; align-items: center; justify-content: space-between; gap: 20rpx; }
.brand { font-size: 50rpx; line-height: 1; font-weight: 700; }
.connection { flex: none; padding: 12rpx 18rpx; border: 2rpx solid #cfd8d2; border-radius: 999rpx; color: #647168; font-size: 24rpx; }
.connection.ok { color: #087342; border-color: #61ad83; background: #edf9f2; }
.connection.warn { color: #92501b; border-color: #d3a071; background: #fff8e9; }
.control-surface { margin-top: 14rpx; padding: 24rpx; border: 2rpx solid #cfd8d2; border-radius: 14rpx; background: #fff; display: flex; flex-direction: column; gap: 20rpx; }
.toolbar-row { display: flex; align-items: center; gap: 14rpx; }
.toolbar-label { width: 78rpx; flex: none; color: #647168; font-size: 24rpx; }
.segments { flex: 1; min-width: 0; padding: 6rpx; border-radius: 12rpx; background: #eef3ef; display: grid; gap: 5rpx; }
.segments.modes { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.segments.speeds { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.segment { min-width: 0; height: 68rpx; margin: 0; padding: 0 4rpx; border-radius: 9rpx; background: transparent; color: #536159; font-size: 23rpx; line-height: 68rpx; white-space: nowrap; }
.segment.selected { color: #075f39; background: #fff; box-shadow: 0 2rpx 8rpx rgba(19, 42, 28, .12); }
.front { display: flex; justify-content: center; align-items: center; gap: 10rpx; color: #647168; font-size: 24rpx; }
.front-arrow { color: #152019; font-size: 38rpx; font-weight: 700; }
.panel { min-height: 500rpx; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 18rpx; }
.dpad { width: 450rpx; height: 450rpx; display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 12rpx; }
.drive-key, .rotate-key, .stop, .tool-button, .tilt-toggle, .calibrate-button, .cal-actions button { margin: 0; border: 2rpx solid #aebbb2; border-radius: 12rpx; background: #fff; color: #152019; }
.drive-key { font-size: 60rpx; font-weight: 700; line-height: 1; }
.drive-key:active, .rotate-key:active { color: #086b41; border-color: #58a87c; background: #e5f5ec; }
.drive-key.forward { grid-column: 2; grid-row: 1; }.drive-key.left { grid-column: 1; grid-row: 2; }.drive-key.right { grid-column: 3; grid-row: 2; }.drive-key.back { grid-column: 2; grid-row: 3; }
.drive-key.center-stop { grid-column: 2; grid-row: 2; color: #a13b32; border-color: #d7a19a; background: #fff0ed; font-size: 40rpx; }
.stick { position: relative; width: 460rpx; height: 460rpx; overflow: hidden; border: 4rpx solid #b8c4bc; border-radius: 50%; background: #eef3ef; box-shadow: inset 0 4rpx 20rpx rgba(0,0,0,.06); }
.cross { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); background: #c4cec7; }.cross.vertical { width: 4rpx; height: 82%; }.cross.horizontal { width: 82%; height: 4rpx; }
.knob { position: absolute; left: 50%; top: 50%; width: 138rpx; height: 138rpx; border: 4rpx solid #087144; border-radius: 50%; background: #138653; box-shadow: 0 10rpx 26rpx rgba(0,0,0,.17); }
.dual-panel { width: 100%; }.dual-grid { width: 100%; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20rpx; }
.dual-unit { min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 14rpx; color: #647168; font-size: 24rpx; }
.stick.dual-stick { width: 100%; height: auto; aspect-ratio: 1; }.knob.small { width: 100rpx; height: 100rpx; }
.rotation-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14rpx; }.rotate-key { height: 84rpx; font-size: 46rpx; line-height: 84rpx; }
.metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10rpx; }
.metrics text { min-width: 0; padding: 14rpx 4rpx; border: 2rpx solid #d9e0db; border-radius: 10rpx; background: #fafcf9; text-align: center; font-family: Consolas, monospace; font-size: 23rpx; overflow: hidden; }
.stop { width: 100%; height: 92rpx; color: #8d2e27; border-color: #d29a91; background: #fff0ed; font-size: 30rpx; font-weight: 700; line-height: 92rpx; }
.tools { margin-top: 20rpx; display: grid; grid-template-columns: 1fr 1fr; gap: 14rpx; }.tool-button { height: 84rpx; font-size: 25rpx; line-height: 84rpx; }
.calibration { margin-top: 26rpx; padding: 22rpx 2rpx; border-top: 2rpx solid #cfd8d2; border-bottom: 2rpx solid #cfd8d2; display: flex; flex-direction: column; gap: 14rpx; }
.section-title { font-size: 28rpx; font-weight: 700; }.gain-row { display: grid; grid-template-columns: 58rpx 1fr 72rpx; align-items: center; gap: 8rpx; font-family: Consolas, monospace; font-size: 24rpx; }.gain-slider { width: 100%; }
.cal-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 14rpx; }.cal-actions button { height: 76rpx; font-size: 25rpx; line-height: 76rpx; }
.status { display: block; min-height: 70rpx; padding: 18rpx 2rpx 0; color: #647168; font-family: Consolas, monospace; font-size: 22rpx; line-height: 1.5; }
.tilt-panel { gap: 22rpx; }.tilt-stage { position: relative; width: 360rpx; height: 360rpx; overflow: hidden; border: 4rpx solid #b8c4bc; border-radius: 50%; background: #eef3ef; }.tilt-stage.armed { border-color: #57a77b; background: #eaf7f0; }.tilt-stage.calibrating { border-color: #d3a071; }
.tilt-axis { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); background: #c4cec7; }.tilt-axis.x-axis { width: 80%; height: 4rpx; }.tilt-axis.y-axis { width: 4rpx; height: 80%; }
.tilt-dot { position: absolute; left: 50%; top: 50%; width: 86rpx; height: 86rpx; border: 4rpx solid #087144; border-radius: 50%; background: #138653; box-shadow: 0 8rpx 22rpx rgba(0,0,0,.16); }
.tilt-readout { display: flex; gap: 28rpx; color: #647168; font-family: Consolas, monospace; font-size: 23rpx; }.tilt-actions { width: 100%; display: grid; grid-template-columns: 1fr 1fr; gap: 14rpx; }
.tilt-toggle, .calibrate-button { height: 82rpx; font-size: 25rpx; line-height: 82rpx; }.tilt-toggle.armed { color: #8d2e27; border-color: #d29a91; background: #fff0ed; }.calibrate-button[disabled] { opacity: .45; }
</style>
