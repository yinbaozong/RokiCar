"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(
  path.join(__dirname, "../app/src/main/assets/index.html"),
  "utf8"
);

for (const tab of ["control", "ai", "return", "settings"]) {
  assert.match(html, new RegExp(`id="tab-${tab}"[^>]*class="[^"]*tab-view`));
  assert.match(html, new RegExp(`data-tab="${tab}"`));
}

assert.match(html, /id="bottom-nav"[^>]*aria-label="主导航"/);
assert.match(html, /id="stop"[^>]*class="[^"]*emergency-stop/);
assert.match(html, /function selectTab\(next\)/);
assert.match(html, /clearMotion\(\);\s*activeTab=next/);
assert.match(html, /localStorage\.setItem\('rokicar-tab',next\)/);

const aiStart = html.indexOf('id="tab-ai"');
const returnStart = html.indexOf('id="tab-return"');
const settingsStart = html.indexOf('id="tab-settings"');
assert.ok(aiStart < html.indexOf('id="voice-toggle"') && html.indexOf('id="voice-toggle"') < returnStart);
assert.ok(returnStart < html.indexOf('id="wifi-return"') && html.indexOf('id="wifi-return"') < settingsStart);
assert.ok(settingsStart < html.indexOf('id="calibration"'));
assert.doesNotMatch(html, /id="square"/, "removed square-test button must stay absent");
assert.match(html, /id="voice-conversation"[^>]*class="[^"]*conversation/);
assert.match(html, /function isRokiCarNetwork\(\)/);
assert.match(html, /element\.textContent='未连接小车'/);

assert.match(html, /\.full-slider-unit\.left\s*\{[^}]*left:max\(/);
assert.match(html, /\.full-slider-unit\.right\s*\{[^}]*right:max\(/);
assert.match(html, /id="full-move-stick"[^>]*class="[^"]*vertical/);
assert.match(html, /id="full-rotate-stick"[^>]*class="[^"]*horizontal/);
assert.match(html, /class="full-rotation-bar"/);
assert.doesNotMatch(html, /data-full-drive|class="full-dpad"/);
assert.match(html, /stickPointers=\{single:null,move:null,rotate:null,fullMove:null,fullRotate:null\}/);
assert.doesNotMatch(html, /id="tilt-drive"|id="tilt-calibrate"|id="tilt-sim"/);
assert.match(html, /id="heading-toggle"[^>]*disabled/);
assert.match(html, /tiltDriving=true;headingTurnEnabled=false/);
assert.match(html, /tiltDriving=!headingTurnEnabled/);
assert.match(html, /if\(raw===null\|\|raw===''\)return WIFI_TARGET/);
assert.match(html, /const WIFI_TARGET=-35/);
assert.match(html, /id="rssi-target-input"[^>]*value="-35"/);
assert.match(html, /id="rssi-rate"/);
assert.match(html, /id="rssi-age"/);
assert.match(html, /filtered\.toFixed\(1\)/);
assert.match(html, /rssiPollTimes\.push\(time\)/);
assert.match(html, /const changed=lastObservedRssi===null\|\|value!==lastObservedRssi/);

const keywordFile = fs.readFileSync(
  path.join(__dirname, "../app/src/main/assets/kws/keywords.txt"),
  "utf8"
);
assert.match(keywordFile, /@小麦小麦/);

console.log("RokiCar tab layout tests passed");
