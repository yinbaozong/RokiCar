/* Accessory lights have no motion heartbeat and never replay on reconnect. */
(() => {
  const panel = document.createElement('div');
  panel.className = 'cal-step';
  panel.innerHTML = `<h3>RGB 灯光</h3>
    <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;padding:12px 0">
      <label><input id="light-power" type="checkbox" disabled> 开灯</label>
      <label>颜色 <input id="light-color" type="color" value="#00ff60" aria-label="灯光颜色" disabled></label>
      <label>亮度 <input id="light-level" type="range" min="5" max="100" value="30" disabled> <output id="light-percent">30%</output></label>
    </div><p id="light-state" role="status">等待连接与灯控固件确认</p>`;
  document.querySelector('#tab-settings .section-heading').after(panel);
  const power = panel.querySelector('#light-power');
  const color = panel.querySelector('#light-color');
  const level = panel.querySelector('#light-level');
  const status = panel.querySelector('#light-state');
  let socket = null, ready = false, pending = null, queryAt = 0, queryCount = 0;
  function enable(value) {
    ready = value;
    [power, color, level].forEach(el => el.disabled = !value);
  }
  function apply() {
    if (!ready) return;
    const hex = color.value.slice(1);
    const rgb = [0, 2, 4].map(i => power.checked ? Math.round(parseInt(hex.slice(i, i + 2), 16) * Number(level.value) / 100) : 0);
    pending = {rgb, at: Date.now(), attempts: 1};
    send(12, ...rgb);
    status.textContent = '等待小车确认…';
  }
  power.addEventListener('change', apply);
  color.addEventListener('change', apply);
  level.addEventListener('input', () => panel.querySelector('#light-percent').textContent = `${level.value}%`);
  level.addEventListener('change', apply);
  setInterval(() => {
    if (socket !== ws) {
      socket = ws;
      pending = null;
      queryAt = 0;
      queryCount = 0;
      enable(false);
      status.textContent = '等待连接与灯控固件确认';
      if (socket) socket.addEventListener('message', event => {
        if (socket !== event.target) return;
        let data;
        try { data = JSON.parse(event.data); } catch (_) { return; }
        if ('lightReady' in data) {
          enable(data.lightReady === true);
          if (!ready) status.textContent = '需要更新核心板灯控程序';
        }
        if (data.lightError) { pending = null; status.textContent = '灯光输出失败，请检查核心板程序'; }
        if (Array.isArray(data.light) && ready) {
          if (pending && !data.light.every((c, i) => c === pending.rgb[i])) return;
          pending = null;
          power.checked = data.light.some(c => c > 0);
          status.textContent = power.checked ? '灯光已开启' : '灯光已关闭';
        }
      });
    }
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      enable(false);
      pending = null;
      status.textContent = '未连接，灯光状态未知';
    }
    if (socket && socket.readyState === WebSocket.OPEN && !ready && queryCount < 10 && Date.now() - queryAt >= 750) {
      queryAt = Date.now();
      queryCount++;
      send(QUERY_CONFIG);
      status.textContent = queryCount === 10 ? '灯控未就绪，请检查固件或重新连接' : '正在同步灯光状态…';
    }
    if (pending && Date.now() - pending.at >= 500) {
      if (pending.attempts >= 4) {
        pending = null;
        status.textContent = '未收到确认，请重试';
      } else {
        pending.at = Date.now();
        pending.attempts++;
        send(12, ...pending.rgb);
      }
    }
  }, 250);
})();
