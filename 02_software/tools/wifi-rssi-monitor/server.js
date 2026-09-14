"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const { execFile } = require("child_process");

const PORT = Number(process.env.PORT || 8765);
const ADB = process.env.ADB || "C:\\Users\\win11\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe";
const clients = new Set();
let latest = { connected: false, rssi: null, ssid: null, serial: null, error: "等待手机" };
let polling = false;

function runAdb(args) {
  return new Promise((resolve, reject) => {
    execFile(ADB, args, { timeout: 5000, windowsHide: true, maxBuffer: 4 * 1024 * 1024 }, (error, stdout) => {
      if (error) reject(error);
      else resolve(stdout);
    });
  });
}

async function physicalSerial() {
  const output = await runAdb(["devices"]);
  const devices = output.split(/\r?\n/)
    .map(line => line.trim().split(/\s+/))
    .filter(parts => parts.length >= 2 && parts[1] === "device" && !parts[0].startsWith("emulator-"));
  return devices[0] ? devices[0][0] : null;
}

async function sample() {
  if (polling) return;
  polling = true;
  try {
    const serial = await physicalSerial();
    if (!serial) throw new Error("未检测到 USB 调试手机");
    const output = await runAdb(["-s", serial, "shell", "dumpsys", "wifi"]);
    const line = output.split(/\r?\n/).find(value => value.includes("mWifiInfo SSID:"));
    const ssid = line && line.match(/SSID:\s*"([^"]+)"/);
    const rssi = line && line.match(/RSSI:\s*(-?\d+)/);
    const speed = line && line.match(/Link speed:\s*(-?\d+)Mbps/);
    if (!ssid || !rssi || Number(rssi[1]) <= -127) throw new Error("手机没有连接 Wi-Fi");
    latest = {
      connected: true,
      serial,
      ssid: ssid[1],
      rssi: Number(rssi[1]),
      linkSpeed: speed ? Number(speed[1]) : null,
      timestamp: Date.now(),
      error: null
    };
  } catch (error) {
    latest = { connected: false, rssi: null, ssid: null, serial: null, timestamp: Date.now(), error: error.message };
  } finally {
    polling = false;
    const packet = `data: ${JSON.stringify(latest)}\n\n`;
    for (const client of clients) client.write(packet);
  }
}

setInterval(sample, 800);
sample();

const server = http.createServer((request, response) => {
  if (request.url === "/events") {
    response.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "Access-Control-Allow-Origin": "*"
    });
    response.write(`data: ${JSON.stringify(latest)}\n\n`);
    clients.add(response);
    request.on("close", () => clients.delete(response));
    return;
  }
  if (request.url === "/api/status") {
    response.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    response.end(JSON.stringify(latest));
    return;
  }
  const file = path.join(__dirname, "index.html");
  response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
  fs.createReadStream(file).pipe(response);
});

server.listen(PORT, "127.0.0.1", () => {
  process.stdout.write(`OmniCar RSSI monitor: http://127.0.0.1:${PORT}\n`);
});
