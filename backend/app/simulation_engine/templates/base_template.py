from __future__ import annotations

import json
from typing import Any

from app.simulation_engine.schemas import SimulationSpecification


# ---------------------------------------------------------------------------
# Shared ControlsManager JS — injected once into every simulation.
# Each subject template should reference SHARED_CONTROLS_MANAGER instead of
# copy-pasting the same ControlsManager class.
# ---------------------------------------------------------------------------
SHARED_CONTROLS_MANAGER = """
class ControlsManager {
  constructor(state, bus) {
    this.state = state;
    this.bus = bus;
    this.sliders = [];
    this._precisions = {};  // key → decimal places override
  }

  /** Register a precision override for a specific parameter id.
   *  e.g.  controls.setPrecision('volume', 4) */
  setPrecision(key, decimals) {
    this._precisions[key] = decimals;
  }

  _fmt(key, val) {
    if (typeof val !== 'number') return String(val);
    const p = this._precisions[key] !== undefined ? this._precisions[key] : 2;
    return val.toFixed(p);
  }

  bind() {
    const self = this;
    document.querySelectorAll('input[type="range"]').forEach(function(input) {
      if (input.id === 'speed-slider') return;
      const key = input.id;
      self.sliders.push(input);
      self.state.set(key, parseFloat(input.value));
      input.addEventListener('input', function() {
        const val = parseFloat(this.value);
        self.state.set(key, val);
        const badge = document.getElementById('badge-' + key);
        if (badge) badge.textContent = self._fmt(key, val);
      });
    });
  }

  sync() {
    this.sliders.forEach(function(input) {
      const val = this.state.get(input.id);
      if (val !== undefined) input.value = val;
    }, this);
  }

  syncLabels() {
    const all = this.state.getAll();
    const self = this;
    this.sliders.forEach(function(input) {
      const val = all[input.id];
      if (val !== undefined) {
        const badge = document.getElementById('badge-' + input.id);
        if (badge) badge.textContent = self._fmt(input.id, val);
      }
    });
  }
}

class AssessmentEngine {
  constructor(state, bus) { this.state = state; this.bus = bus; }
  getCurrentQuestion() { return document.getElementById('assess-q')?.textContent || ''; }
}
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>__TITLE__</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: transparent;
    color: #1e293b;
    padding: 0;
    margin: 0;
    overflow-x: hidden;
  }
  #sim-container {
    max-width: 1100px;
    width: 100%;
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    overflow: hidden;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    margin: auto;
  }
  /* ── Header ── */
  .sim-header {
    padding: 16px 24px;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    background: #ffffff;
  }
  .sim-header h1 { 
    font-size: 20px; 
    font-weight: 800; 
    color: #1800ad; 
    letter-spacing: -0.3px;
  }
  .sim-header .obj { font-size: 12px; color: #64748b; line-height: 1.5; margin-top: 3px; max-width: 600px; }
  .sim-badge {
    font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px;
    padding: 4px 12px; border-radius: 20px; 
    background: rgba(24, 0, 173, 0.06);
    color: #1800ad; border: 1px solid rgba(24, 0, 173, 0.15); 
    white-space: nowrap; flex-shrink: 0;
  }
  /* ── Layout ── */
  .sim-body { display: flex; flex-direction: column; }
  @media (min-width: 820px) { .sim-body { flex-direction: row; } }
  
  /* ── Canvas area ── */
  .sim-visual {
    flex: 1; padding: 16px; display: flex; flex-direction: column;
    align-items: center; justify-content: center; min-height: 440px;
    background: #f8fafc; position: relative;
  }
  .sim-visual canvas {
    width: 100%; max-width: __CANVAS_WIDTH__px; height: auto;
    aspect-ratio: __CANVAS_WIDTH__ / __CANVAS_HEIGHT__;
    border-radius: 12px; border: 1px solid #e2e8f0;
    background: #ffffff; touch-action: none; cursor: crosshair;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    display: block;
  }
  .canvas-hint {
    font-size: 11px; color: #64748b; margin-top: 8px;
    text-align: center; font-style: italic; min-height: 16px;
    font-weight: 500;
  }
  /* ── Side panel ── */
  .sim-panel {
    width: 100%; max-width: 290px; padding: 16px;
    border-left: 1px solid #e2e8f0;
    display: flex; flex-direction: column; gap: 12px;
    background: #ffffff; overflow-y: auto; max-height: 700px;
  }
  @media (max-width: 819px) {
    .sim-panel { max-width: 100%; border-left: none; border-top: 1px solid #e2e8f0; max-height: none; }
    .sim-visual { min-height: 320px; }
  }
  /* ── Section label ── */
  .section-label {
    font-size: 10px; font-weight: 800; text-transform: uppercase;
    letter-spacing: 1.2px; color: #94a3b8; margin-bottom: -2px;
  }
  /* ── Slider controls ── */
  .ctrl { display: flex; flex-direction: column; gap: 4px; }
  .ctrl-label {
    font-size: 11px; font-weight: 600; color: #334155;
    display: flex; justify-content: space-between; align-items: center;
  }
  .ctrl-label .val-badge {
    background: rgba(24, 0, 173, 0.06); color: #1800ad;
    padding: 2px 8px; border-radius: 8px; font-size: 11px;
    font-family: 'JetBrains Mono', monospace; font-weight: 700;
    min-width: 46px; text-align: center;
    border: 1px solid rgba(24, 0, 173, 0.12);
  }
  .ctrl-unit { font-size: 10px; color: #94a3b8; margin-left: 2px; }
  input[type="range"] {
    width: 100%; height: 5px; -webkit-appearance: none; appearance: none;
    background: #e2e8f0; border-radius: 4px; outline: none; cursor: pointer;
    margin: 4px 0 0;
  }
  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none; width: 18px; height: 18px;
    border-radius: 50%; background: #1800ad;
    border: 2px solid #ffffff; cursor: pointer;
    box-shadow: 0 2px 4px rgba(24, 0, 173, 0.25);
    transition: transform 0.1s, box-shadow 0.1s;
  }
  input[type="range"]::-webkit-slider-thumb:hover { 
    transform: scale(1.2); 
    box-shadow: 0 2px 8px rgba(24, 0, 173, 0.4); 
  }
  input[type="range"]::-moz-range-thumb {
    width: 18px; height: 18px; border-radius: 50%;
    background: #1800ad; border: 2px solid #ffffff; cursor: pointer;
    box-shadow: 0 2px 4px rgba(24, 0, 173, 0.25);
  }
  input[type="range"]:focus-visible { outline: 2px solid #1800ad; outline-offset: 3px; }
  
  /* ── Buttons ── */
  .actions { display: flex; gap: 6px; flex-wrap: wrap; }
  .actions button {
    flex: 1; min-width: 54px; padding: 8px 10px; border: 1px solid #cbd5e1;
    border-radius: 8px; background: #ffffff; color: #475569;
    font-size: 11px; font-weight: 700; cursor: pointer;
    transition: all 0.12s; text-transform: uppercase; letter-spacing: 0.3px;
    display: flex; align-items: center; justify-content: center; gap: 5px;
  }
  .actions button:hover { 
    background: #f8fafc; 
    border-color: #94a3b8; 
    color: #1e293b; 
    transform: translateY(-1px); 
  }
  .actions button:active { transform: scale(0.97) translateY(0); }
  .actions button.primary { 
    background: #1800ad; 
    border-color: #1800ad; 
    color: #ffffff; 
    box-shadow: 0 2px 6px rgba(24, 0, 173, 0.2);
  }
  .actions button.primary:hover { 
    background: #14008a; 
  }
  .actions button.running { 
    background: #10b981; 
    border-color: #10b981; 
    color: #ffffff; 
  }
  .actions button.running:hover { 
    background: #059669; 
  }
  /* ── Presets ── */
  .presets { display: flex; gap: 4px; flex-wrap: wrap; }
  .presets button {
    padding: 4px 10px; border: 1px solid #e2e8f0; border-radius: 6px;
    background: #ffffff; color: #64748b; font-size: 10px; font-weight: 600;
    cursor: pointer; transition: all 0.12s;
  }
  .presets button:hover { 
    background: rgba(24, 0, 173, 0.04); 
    color: #1800ad; 
    border-color: rgba(24, 0, 173, 0.2); 
  }
  /* ── Live value cards ── */
  .values { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .vcard {
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 8px 10px; text-align: center;
    transition: all 0.2s;
  }
  .vcard:hover { 
    border-color: #cbd5e1; 
    transform: translateY(-1px);
  }
  .vcard .lbl { font-size: 8px; font-weight: 800; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.8px; }
  .vcard .num {
    font-size: 15px; font-weight: 800; color: #1800ad;
    font-family: 'JetBrains Mono', monospace; margin-top: 2px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  /* ── Graph ── */
  .graph-area { 
    width: 100%; padding: 12px 20px 16px; 
    border-top: 1px solid #e2e8f0; 
    background: #ffffff; 
  }
  .graph-area canvas {
    width: 100%; height: 160px; border-radius: 10px;
    border: 1px solid #e2e8f0; 
    background: #ffffff; display: block;
  }
  .graph-header {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
  }
  .graph-header .gt { font-size: 12px; font-weight: 800; color: #334155; }
  .graph-header .gl { display: flex; gap: 12px; font-size: 10px; font-weight: 600; }
  .graph-header .gl span { display: flex; align-items: center; gap: 4px; color: #64748b; }
  .graph-header .gl .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
  
  /* ── Assessment ── */
  .assess-area { 
    padding: 14px 24px; 
    border-top: 1px solid #e2e8f0; 
    background: rgba(24, 0, 173, 0.03); 
    border-left: 4px solid #1800ad;
  }
  .assess-area .ql {
    font-size: 9px; font-weight: 800; color: #1800ad;
    text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 4px;
  }
  .assess-area .q { font-size: 13px; line-height: 1.6; color: #1e293b; font-weight: 600; }
  .assess-area .h { font-size: 11px; color: #64748b; margin-top: 6px; font-style: italic; line-height: 1.5; }
  .opt-btn {
    padding: 8px 16px; 
    border: 1px solid #cbd5e1; 
    border-radius: 8px;
    background: #ffffff; 
    color: #475569; 
    font-size: 11px; 
    font-weight: 700;
    cursor: pointer; 
    transition: all 0.15s ease;
    font-family: 'Montserrat', sans-serif;
  }
  .opt-btn:hover:not(:disabled) {
    background: rgba(24, 0, 173, 0.04);
    color: #1800ad;
    border-color: #1800ad;
  }
  .opt-btn:disabled {
    cursor: not-allowed;
  }
  
  /* ── Divider ── */
  .panel-divider { height: 1px; background: #e2e8f0; margin: 3px 0; }
  
  /* ── Responsive tweaks ── */
  @media (max-width: 480px) {
    body { padding: 0; }
    #sim-container { border-radius: 0; border-left: none; border-right: none; }
    .sim-header { padding: 12px 14px 10px; flex-direction: column; gap: 6px; }
    .sim-header h1 { font-size: 16px; }
    .sim-visual { padding: 8px; min-height: 240px; }
    .sim-panel { padding: 12px; }
    .assess-area { padding: 10px 14px; }
    .graph-area { padding: 8px 10px 12px; }
    .graph-area canvas { height: 130px; }
  }
</style>
</head>
<body>
<div id="sim-container" role="application" aria-label="__TITLE__">
  <div class="sim-header">
    <div>
      <h1>__TITLE__</h1>
      <div class="obj">__OBJECTIVE__</div>
    </div>
    <span class="sim-badge">__SUBJECT_BADGE__</span>
  </div>
  <div class="sim-body">
    <div class="sim-visual" id="simulation-area">
      <canvas id="canvas" width="__CANVAS_WIDTH__" height="__CANVAS_HEIGHT__"
              aria-label="Simulation canvas" role="img"></canvas>
      <div class="canvas-hint" id="hint-text"></div>
    </div>
    <div class="sim-panel" id="panel" role="toolbar" aria-label="Controls">
      <div class="section-label">Parameters</div>
      __CONTROLS__
      <div class="panel-divider"></div>
      __SPEED_CONTROL__
      __PRESETS__
      <div class="actions">
        <button class="primary" id="play-btn" aria-label="Play/Pause simulation">
          ▶ Play
        </button>
        <button id="reset-btn" aria-label="Reset simulation" title="Reset">↺ Reset</button>
        <button id="step-btn" aria-label="Step forward" title="Step one frame">▶| Step</button>
      </div>
      <div class="panel-divider"></div>
      <div class="section-label">Live Values</div>
      <div class="values" id="values">
        __LIVE_VALUES__
      </div>
    </div>
  </div>
  __GRAPH__
  __ASSESSMENT__
</div>
<script>
__SCRIPT__
</script>
</body>
</html>"""


CANVAS_BOILERPLATE = """
(function() {
  const SPEC = __SPEC__;

  // ── EventBus ─────────────────────────────────────────────────────────────
  class EventBus {
    constructor() { this._listeners = {}; }
    on(event, fn) { (this._listeners[event] = this._listeners[event] || []).push(fn); return this; }
    off(event, fn) { if (this._listeners[event]) this._listeners[event] = this._listeners[event].filter(f => f !== fn); return this; }
    emit(event, data) { (this._listeners[event] || []).forEach(fn => fn(data)); }
  }

  // ── StateManager ─────────────────────────────────────────────────────────
  class StateManager {
    constructor(initial) {
      this._state = Object.assign({}, initial);
      this._history = [];
      this._maxHistory = 500;
      this._bus = new EventBus();
    }
    get(key) { return this._state[key]; }
    set(key, value) {
      if (this._state[key] === value) return;
      const old = this._state[key];
      this._state[key] = value;
      this._history.push({ key, old, value, time: performance.now() });
      if (this._history.length > this._maxHistory) this._history.shift();
      this._bus.emit('change:' + key, { key, old, value });
      this._bus.emit('change', { key, old, value });
    }
    getAll() { return Object.assign({}, this._state); }
    reset(initial) { this._state = Object.assign({}, initial); this._history = []; this._bus.emit('reset', this._state); }
    on(event, fn) { this._bus.on(event, fn); return this; }
  }

  // ── GraphManager ─────────────────────────────────────────────────────────
  class GraphManager {
    constructor(canvasId) {
      this.canvas = document.getElementById(canvasId);
      if (!this.canvas) return;
      
      const dpr = window.devicePixelRatio || 1;
      const logicalWidth = this.canvas.width || 700;
      const logicalHeight = this.canvas.height || 160;
      
      this.canvas.width = logicalWidth * dpr;
      this.canvas.height = logicalHeight * dpr;
      this.canvas.style.width = logicalWidth + 'px';
      this.canvas.style.height = logicalHeight + 'px';
      
      Object.defineProperty(this.canvas, 'width', {
        configurable: true,
        get: function() { return logicalWidth; }
      });
      Object.defineProperty(this.canvas, 'height', {
        configurable: true,
        get: function() { return logicalHeight; }
      });
      
      this.ctx = this.canvas.getContext('2d');
      this.ctx.scale(dpr, dpr);
      
      this.data = {};           // seriesName → [{x, y}]
      this.maxPoints = 350;
      this.range = { xMin: 0, xMax: 10, yMin: 0, yMax: 10 };
      this.colors = ['#1800ad', '#059669', '#d97706', '#ec4899', '#0284c7', '#8b5cf6'];
    }

    pushData(seriesName, x, y) {
      if (!this.canvas) return;
      if (!this.data[seriesName]) this.data[seriesName] = [];
      const arr = this.data[seriesName];
      arr.push({ x, y });
      if (arr.length > this.maxPoints) arr.shift();
    }

    clear() { this.data = {}; }

    setRange(xMin, xMax, yMin, yMax) {
      this.range = { xMin, xMax, yMin, yMax };
    }

    /** Auto-scale Y to the data currently in the series. */
    autoScaleY(padding) {
      padding = padding || 0.1;
      let yMin = Infinity, yMax = -Infinity;
      Object.values(this.data).forEach(function(pts) {
        pts.forEach(function(p) { if (p.y < yMin) yMin = p.y; if (p.y > yMax) yMax = p.y; });
      });
      if (!isFinite(yMin)) return;
      const margin = Math.abs(yMax - yMin) * padding || 1;
      this.range.yMin = yMin - margin;
      this.range.yMax = yMax + margin;
    }

    draw() {
      if (!this.canvas) return;
      const ctx = this.ctx, c = this.canvas;
      const w = c.width, h = c.height;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h);

      const pad = { t: 16, r: 16, b: 28, l: 48 };
      const pw = w - pad.l - pad.r;
      const ph = h - pad.t - pad.b;
      const { xMin, xMax, yMin, yMax } = this.range;
      const xRange = xMax - xMin || 1;
      const yRange = yMax - yMin || 1;

      // grid
      ctx.strokeStyle = '#f1f5f9'; ctx.lineWidth = 1.0;
      for (let i = 0; i <= 8; i++) {
        const x = pad.l + (i / 8) * pw;
        ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, pad.t + ph); ctx.stroke();
      }
      for (let i = 0; i <= 5; i++) {
        const y = pad.t + (i / 5) * ph;
        ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(pad.l + pw, y); ctx.stroke();
      }

      // axes
      ctx.strokeStyle = '#cbd5e1'; ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(pad.l, pad.t); ctx.lineTo(pad.l, pad.t + ph); ctx.lineTo(pad.l + pw, pad.t + ph);
      ctx.stroke();

      // Y labels
      ctx.fillStyle = '#64748b'; ctx.font = '9px "JetBrains Mono", monospace'; ctx.textAlign = 'right';
      for (let i = 0; i <= 4; i++) {
        const yVal = yMin + (yRange * i) / 4;
        const yp = pad.t + ph - (i / 4) * ph;
        ctx.fillText(yVal.toFixed(1), pad.l - 5, yp + 3);
      }
      // X labels
      ctx.textAlign = 'center';
      for (let i = 0; i <= 4; i++) {
        const xVal = xMin + (xRange * i) / 4;
        const xp = pad.l + (i / 4) * pw;
        ctx.fillText(xVal.toFixed(1), xp, pad.t + ph + 16);
      }

      // series
      let colorIdx = 0;
      const self = this;
      Object.entries(this.data).forEach(function([name, points]) {
        if (points.length < 2) return;
        const color = self.colors[colorIdx++ % self.colors.length];
        ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.lineJoin = 'round';
        ctx.beginPath();
        points.forEach(function(p, i) {
          const x = pad.l + ((p.x - xMin) / xRange) * pw;
          const y = pad.t + ph - ((p.y - yMin) / yRange) * ph;
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
        // dot at latest point
        const last = points[points.length - 1];
        const lx = pad.l + ((last.x - xMin) / xRange) * pw;
        const ly = pad.t + ph - ((last.y - yMin) / yRange) * ph;
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(lx, ly, 3.5, 0, Math.PI * 2); ctx.fill();
      });
    }
  }

  // ── User-defined simulation classes injected here ─────────────────────
  __CLASSES__

  // ── Bootstrap ────────────────────────────────────────────────────────────
  function init() {
    const canvas = document.getElementById('canvas');
    if (canvas) {
      const dpr = window.devicePixelRatio || 1;
      const logicalWidth = canvas.width || 600;
      const logicalHeight = canvas.height || 400;
      
      canvas.width = logicalWidth * dpr;
      canvas.height = logicalHeight * dpr;
      
      // Allow CSS to handle responsiveness, enforcing max-width logical constraint
      canvas.style.width = '100%';
      canvas.style.maxWidth = logicalWidth + 'px';
      canvas.style.height = 'auto';
      
      Object.defineProperty(canvas, 'width', {
        configurable: true,
        get: function() { return logicalWidth; }
      });
      Object.defineProperty(canvas, 'height', {
        configurable: true,
        get: function() { return logicalHeight; }
      });
      
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
    }

    const state  = new StateManager(__INITIAL_STATE__);
    const bus    = new EventBus();
    const graphEl = document.getElementById('graph-canvas');
    const graphMgr = graphEl ? new GraphManager('graph-canvas') : null;

    const engine     = new SimulationEngine(canvas, state, bus);
    const renderer   = new Renderer(canvas, state, bus);
    const controls   = new ControlsManager(state, bus);
    const assessment = new AssessmentEngine(state, bus);

    window._engine   = engine;
    window._state    = state;
    window._graphMgr = graphMgr;

    let running  = false;   // starts paused — user presses Play
    let lastTime = 0;
    let simSpeed = 1;
    let stepMode = false;

    // ── DOM helpers ──────────────────────────────────────────────────────
    const playBtn  = document.getElementById('play-btn');
    const playIcon = playBtn;

    function setRunning(val) {
      running = val;
      if (running) {
        playBtn.textContent = '⏸ Pause';
        playBtn.classList.remove('primary');
        playBtn.classList.add('running');
      } else {
        playBtn.textContent = '▶ Play';
        playBtn.classList.remove('running');
        playBtn.classList.add('primary');
      }
    }

    function updateDisplayedValues() {
      const all = state.getAll();
      Object.entries(all).forEach(function([key, val]) {
        const el = document.getElementById('val-' + key);
        if (el) {
          if (typeof val === 'number') {
            const p = parseInt(el.dataset.precision, 10);
            el.textContent = val.toFixed(isNaN(p) ? 2 : p);
          } else {
            el.textContent = val;
          }
        }
      });
      const hintEl = document.getElementById('hint-text');
      if (hintEl && engine.getHint) hintEl.textContent = engine.getHint();
    }

    // ── Render loop ──────────────────────────────────────────────────────
    function loop(time) {
      const rawDt = lastTime ? (time - lastTime) / 1000 : 0.016;
      // clamp dt so a tab-pause doesn't explode the sim
      const dt = Math.min(rawDt, 0.05) * simSpeed;
      lastTime = time;

      if ((running || stepMode) && !(!running && !stepMode)) {
        if (running || stepMode) {
          engine.update(dt, state);
          __GRAPH_DATA_PUSH__
          updateDisplayedValues();
          controls.syncLabels();
        }
        if (stepMode) { stepMode = false; running = false; setRunning(false); }
      }
      renderer.draw(dt, state);
      if (graphMgr) graphMgr.draw();
      bus.emit('render', { time, dt });
      requestAnimationFrame(loop);
    }

    // ── Control bindings ─────────────────────────────────────────────────
    playBtn.addEventListener('click', function() { setRunning(!running); });

    document.getElementById('reset-btn').addEventListener('click', function() {
      state.reset(__INITIAL_STATE__);
      if (graphMgr) { graphMgr.clear(); graphMgr.setRange(0, 10, 0, 10); }
      if (engine.onReset) engine.onReset();
      controls.sync();
      updateDisplayedValues();
      lastTime = 0;
      setRunning(false);
    });

    const stepBtn = document.getElementById('step-btn');
    if (stepBtn) {
      stepBtn.addEventListener('click', function() {
        stepMode = true;
        // Ensure one frame runs even if paused
        if (!running) {
          engine.update(0.016 * simSpeed, state);
          __GRAPH_DATA_PUSH__
          updateDisplayedValues();
          controls.syncLabels();
          renderer.draw(0.016, state);
          if (graphMgr) graphMgr.draw();
          stepMode = false;
        }
      });
    }

    const speedSlider = document.getElementById('speed-slider');
    if (speedSlider) {
      speedSlider.addEventListener('input', function() {
        simSpeed = parseFloat(this.value);
        document.getElementById('speed-label').textContent = simSpeed.toFixed(1) + '×';
      });
    }

    if (engine.canvasInteractions) engine.canvasInteractions(canvas, state, bus);

    controls.bind();
    updateDisplayedValues();
    // Draw one static frame immediately so canvas isn't blank
    renderer.draw(0, state);
    requestAnimationFrame(loop);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
"""


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def build_simulation_html(
    spec: SimulationSpecification,
    custom_script: str = "",
    custom_controls: str = "",
    custom_live_values: str = "",
    custom_graph: str = "",
    custom_assessment: str = "",
    custom_presets: str = "",
) -> str:
    title      = spec.title
    objective  = spec.learning_objectives[0] if spec.learning_objectives else f"Explore {spec.topic}"
    subject_badge = spec.subject.value.upper() if spec.subject else "SIMULATION"

    controls_html    = custom_controls    or _build_controls_html(spec)
    live_values_html = custom_live_values or _build_live_values_html(spec)
    graph_html       = ""
    assessment_html  = custom_assessment  or _build_assessment_html(spec)
    presets_html     = custom_presets     or ""
    script_content   = _build_script(spec, custom_script)

    speed_control = """  <div class="ctrl">
    <div class="ctrl-label">
      <span>Sim Speed</span>
      <span class="val-badge" id="speed-label">1.0×</span>
    </div>
    <input type="range" id="speed-slider" min="0.1" max="4" step="0.1" value="1" aria-label="Simulation speed">
  </div>"""

    result = HTML_TEMPLATE
    result = result.replace("__TITLE__",        title)
    result = result.replace("__OBJECTIVE__",    objective)
    result = result.replace("__SUBJECT_BADGE__",subject_badge)
    result = result.replace("__CANVAS_WIDTH__", str(spec.canvas_width))
    result = result.replace("__CANVAS_HEIGHT__",str(spec.canvas_height))
    result = result.replace("__CONTROLS__",     controls_html)
    result = result.replace("__LIVE_VALUES__",  live_values_html)
    result = result.replace("__GRAPH__",        graph_html)
    result = result.replace("__ASSESSMENT__",   assessment_html)
    result = result.replace("__PRESETS__",      presets_html)
    result = result.replace("__SPEED_CONTROL__",speed_control)
    result = result.replace("__SCRIPT__",       script_content)

    return result


# ---------------------------------------------------------------------------
# Script builder
# ---------------------------------------------------------------------------

def _build_script(spec: SimulationSpecification, custom_script: str) -> str:
    classes_code = custom_script if custom_script else _default_classes()

    # Always append the shared ControlsManager + AssessmentEngine so subject
    # templates only need to supply SimulationEngine + Renderer.
    # Subject templates that define their own ControlsManager are responsible
    # for NOT importing the shared one by passing include_shared=False.
    classes_code = classes_code + "\n" + SHARED_CONTROLS_MANAGER

    initial_state    = _build_initial_state(spec)
    spec_json        = json.dumps(spec.raw_spec or spec.dict())
    graph_data_push  = _build_graph_data_push(spec)

    script = CANVAS_BOILERPLATE
    script = script.replace("__SPEC__",          spec_json)
    script = script.replace("__CLASSES__",       classes_code)
    script = script.replace("__INITIAL_STATE__", json.dumps(initial_state))
    script = script.replace("__GRAPH_DATA_PUSH__", graph_data_push)

    return script


def _build_graph_data_push(spec: SimulationSpecification) -> str:
    """Generate sensible graph push code from spec, or empty string."""
    return ""


def _build_initial_state(spec: SimulationSpecification) -> dict:
    state: dict = {}
    for p in spec.parameters:
        state[p.id] = p.default
    state["output"] = 0
    state["time"]   = 0
    return state


# ---------------------------------------------------------------------------
# HTML snippet builders
# ---------------------------------------------------------------------------

def _build_controls_html(spec: SimulationSpecification) -> str:
    if not spec.parameters:
        return ""
    return "\n".join(
        _control_html(p.id, p.name, p.symbol, p.default, p.min, p.max, p.step, p.unit, p.description)
        for p in spec.parameters
    )


def _control_html(cid, name, symbol, default, min_v, max_v, step, unit, desc):
    label = f"{name}"
    if symbol and symbol != name:
        label += f" ({symbol})"
    return (
        f'    <div class="ctrl">\n'
        f'      <div class="ctrl-label">\n'
        f'        <span>{label} <span class="ctrl-unit">{unit}</span></span>\n'
        f'        <span class="val-badge" id="badge-{cid}">{default}</span>\n'
        f'      </div>\n'
        f'      <input type="range" id="{cid}" min="{min_v}" max="{max_v}" step="{step}" value="{default}"\n'
        f'             aria-label="{name}" title="{desc}">\n'
        f'    </div>'
    )


def _build_live_values_html(spec: SimulationSpecification) -> str:
    if not spec.parameters:
        return ""
    colors = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#8b5cf6']
    parts = []
    for i, p in enumerate(spec.parameters[:6]):
        color = colors[i % len(colors)]
        parts.append(_value_card_html(p.symbol or p.name, p.id, p.default, color))
    if spec.equations:
        parts.append(_value_card_html("Output", "output", 0, "#06b6d4"))
    return "\n".join(parts)


def _value_card_html(label, vid, default_val, color=None):
    style = f' style="color:{color}"' if color else ""
    return (
        f'    <div class="vcard">\n'
        f'      <div class="lbl">{label}</div>\n'
        f'      <div class="num" id="val-{vid}"{style}>{default_val}</div>\n'
        f'    </div>'
    )


def _build_graph_html(spec: SimulationSpecification) -> str:
    return ""


def _build_assessment_html(spec: SimulationSpecification) -> str:
    if not spec.assessment_prompts:
        return ""
    ap = spec.assessment_prompts[0]
    
    options = getattr(ap, 'options', None)
    if not options or len(options) < 2:
        options = ["Increases", "Decreases", "Doubles", "Remains unchanged"]
    correct_idx = getattr(ap, 'correct_answer', 0)
    
    options_html = ""
    for idx, opt in enumerate(options):
        options_html += (
            f'      <button class="opt-btn" onclick="checkAnswer({idx}, {correct_idx})">{opt}</button>\n'
        )
        
    return (
        f'  <div class="assess-area" id="prediction-mcq-area">\n'
        f'    <div class="ql">Predict It</div>\n'
        f'    <div class="q" id="assess-q">{ap.question}</div>\n'
        f'    <div class="options-container" style="display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;">\n'
        f'{options_html}'
        f'    </div>\n'
        f'    <div class="feedback-msg" id="mcq-feedback" style="display: none; margin-top: 10px; font-size: 12px; font-weight: 700;"></div>\n'
        f'    <div class="h" id="assess-h" style="display: none; margin-top: 6px; font-size: 11px; color: #64748b; font-style: italic;">Hint: {ap.hint}</div>\n'
        f'  </div>\n'
        f'  <script>\n'
        f'    function checkAnswer(chosenIdx, correctIdx) {{\n'
        f'      const feedbackEl = document.getElementById("mcq-feedback");\n'
        f'      const hintEl = document.getElementById("assess-h");\n'
        f'      const buttons = document.querySelectorAll("#prediction-mcq-area .opt-btn");\n'
        f'      buttons.forEach((btn, idx) => {{\n'
        f'        btn.disabled = true;\n'
        f'        if (idx === correctIdx) {{\n'
        f'          btn.style.background = "#d1fae5";\n'
        f'          btn.style.borderColor = "#10b981";\n'
        f'          btn.style.color = "#065f46";\n'
        f'        }} else if (idx === chosenIdx) {{\n'
        f'          btn.style.background = "#fee2e2";\n'
        f'          btn.style.borderColor = "#ef4444";\n'
        f'          btn.style.color = "#991b1b";\n'
        f'        }}\n'
        f'      }});\n'
        f'      feedbackEl.style.display = "block";\n'
        f'      if (chosenIdx === correctIdx) {{\n'
        f'        feedbackEl.textContent = "✓ Correct prediction! Run the simulation below to verify and see it in action.";\n'
        f'        feedbackEl.style.color = "#10b981";\n'
        f'      }} else {{\n'
        f'        feedbackEl.textContent = "✗ Not quite! Let\'s test the correct outcome by playing the simulation below.";\n'
        f'        feedbackEl.style.color = "#ef4444";\n'
        f'      }}\n'
        f'      if (hintEl) hintEl.style.display = "block";\n'
        f'    }}\n'
        f'  </script>\n'
    )


# ---------------------------------------------------------------------------
# Default (stub) classes — used when no custom script is provided
# ---------------------------------------------------------------------------

def _default_classes() -> str:
    return """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
  }
  update(dt, state) {}
  onReset() {}
  getHint() { return 'Press Play to begin, then adjust controls.'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
  }
  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#f8fafc'; ctx.fillRect(0, 0, w, h);

    // subtle grid
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 16px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('Simulation Ready', w / 2, h / 2 - 12);
    ctx.font = '12px sans-serif'; ctx.fillStyle = '#64748b';
    ctx.fillText('Press ▶ Play to begin', w / 2, h / 2 + 14);
    ctx.textAlign = 'left';
  }
}
"""


# ---------------------------------------------------------------------------
# LLM-generated simulation (for topics without a built-in template)
# ---------------------------------------------------------------------------

def build_custom_llm_simulation(spec: SimulationSpecification) -> str:
    """Generate SimulationEngine + Renderer JS via LLM for arbitrary topics.
    Returns JS string containing exactly those two classes.
    ControlsManager and AssessmentEngine are appended automatically by
    _build_script() via SHARED_CONTROLS_MANAGER.
    """
    from app.simulation_engine.prompt_understanding_layer import query_llm

    objectives_text = "; ".join(spec.learning_objectives) if spec.learning_objectives else spec.topic
    params_text = "\n".join(
        f"  - id='{p.id}'  name='{p.name}'  symbol='{p.symbol}'  "
        f"range=[{p.min}, {p.max}]  default={p.default}  unit='{p.unit}'"
        for p in spec.parameters
    ) if spec.parameters else "  (no predefined parameters — choose appropriate ones)"

    canvas_w = spec.canvas_width
    canvas_h = spec.canvas_height

    llm_prompt = f"""You are a senior front-end developer and creative tech designer.
Your task is to write raw JavaScript that defines two classes: SimulationEngine and Renderer.
These classes will run inside a premium light-themed educational canvas simulation.

TOPIC: {spec.topic}
SUBJECT: {spec.subject.value.upper()}
LEARNING OBJECTIVES: {objectives_text}
CANVAS SIZE: {canvas_w} × {canvas_h} pixels

PARAMETERS available to read/write via state:
{params_text}

━━ REQUIREMENTS & CODE STYLE ━━
1. HTML5 Canvas size is exactly {canvas_w}x{canvas_h}. The background color of the canvas is white `#ffffff` or `#f8fafc` (already cleared in the template).
2. Use clean, high-contrast, premium color accents inspired by the brand (e.g. Royal Blue `#1800ad`, Slate Grey `#475569`, Sky Blue `#0284c7`, Emerald Green `#059669`, Amber `#d97706`, Crimson Red `#dc2626`) for all objects, particles, paths, and annotations.
3. Avoid neon glows or excessive shadows. Keep visuals crisp and flat. You can use standard drop shadows (e.g. `ctx.shadowColor = 'rgba(0,0,0,0.06)'; ctx.shadowBlur = 6;`) sparingly for depth on draggable handles, but keep all line paths, text labels, and grid coordinates sharp and clean.
4. Direct Canvas Drag Interactions (CRITICAL FOR HIGH ENGAGEMENT):
   - You MUST implement direct mouse/touch interaction in `canvasInteractions(canvas, state, bus)`!
   - Define draggable handles (e.g., handles, dots, vectors, or particles) directly on the canvas.
   - On mousedown/touchstart and touchmove/mousemove, touch/mouse event coordinates must be scaled properly to support both mobile and desktop screen sizes:
     ```javascript
     const rect = canvas.getBoundingClientRect();
     const clientX = e.touches && e.touches[0] ? e.touches[0].clientX : e.clientX;
     const clientY = e.touches && e.touches[0] ? e.touches[0].clientY : e.clientY;
     const x = (clientX - rect.left) * (canvas.width / rect.width);
     const y = (clientY - rect.top) * (canvas.height / rect.height);
     ```
     Use these logical coordinates `x` and `y` for hit testing and dragging calculations. This is critical to ensure interactive elements are accurate and responsive when the canvas scales down on smaller screens.
   - Update `canvas.style.cursor` to `'grab'` on hover and `'grabbing'` on drag to give strong visual affordance.
5. High-fidelity Fluid Animations:
   - Add animations like trailing paths (remember past positions in a trail array), smooth particle flows (e.g. current drift, magnetic field lines, moving atoms), wave ripples, or glowing pulse dots traveling along path lines to make the canvas feel alive.
6. Elegant HUD Overlay:
   - Draw a beautiful, light-themed HUD overlay card directly on the canvas in a corner:
     `ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';`
     `ctx.strokeStyle = 'rgba(24, 0, 173, 0.12)';`
     `ctx.lineWidth = 1;`
     `ctx.beginPath();`
     `ctx.roundRect(15, 15, 240, 95, 10);`
     `ctx.fill();`
     `ctx.stroke();`
     And print at least 3 live variables/formulas using a dark slate color `#1e293b` or `#1800ad`.
7. Avoid divide-by-zero or out-of-bounds positions by clamping states properly.

OUTPUT STRUCTURE:
Output ONLY the raw JavaScript code defining:
- `class SimulationEngine`
- `class Renderer`
Absolutely NO markdown fences, NO HTML, and NO explanation text.

━━ CLASS 1 template ━━
class SimulationEngine {{
  constructor(canvas, state, bus) {{
    this.canvas = canvas;
    this.state = state;
    this.bus = bus;
    this.time = 0;
    this.dragging = null; // tracking drag node
  }}
  update(dt, state) {{
    this.time += dt;
    // dt in seconds. Read sliders: state.get('param')
    // Compute physics, check bounds. Set output state keys.
  }}
  onReset() {{
    this.time = 0;
  }}
  getHint() {{
    return 'Click and drag elements directly on the canvas to interact!';
  }}
  canvasInteractions(canvas, state, bus) {{
    // bind mousedown, mousemove, mouseup, touchstart, touchmove, touchend
  }}
}}

━━ CLASS 2 template ━━
class Renderer {{
  constructor(canvas, state, bus) {{
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.state = state;
    this.bus = bus;
  }}
  draw(dt, state) {{
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h);
    
    // Draw subtle grid
    ctx.strokeStyle = 'rgba(24, 0, 173, 0.05)'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 40) {{ ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }}
    for (let y = 0; y < h; y += 40) {{ ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }}
    
    // Draw main physics visualization using clean, crisp brand-aligned styles
    
    // Draw HUD glass panel with key values
  }}
}}
"""

    try:
        js_code = query_llm(llm_prompt, temperature=0.25)
        js_code = js_code.strip()
        # strip markdown fences if model ignores instructions
        if js_code.startswith("```"):
            js_code = js_code[js_code.find("\n") + 1:]
        if js_code.endswith("```"):
            js_code = js_code[:-3].rstrip()
        js_code = js_code.strip()

        # Sanity-check
        if "class SimulationEngine" not in js_code or "class Renderer" not in js_code:
            return _default_classes()

        # Strip any ControlsManager/AssessmentEngine the model may have hallucinated
        # (shared ones are appended by _build_script)
        for cls in ("class ControlsManager", "class AssessmentEngine"):
            idx = js_code.find(cls)
            if idx != -1:
                js_code = js_code[:idx].rstrip()

        return js_code

    except Exception:
        return _default_classes()