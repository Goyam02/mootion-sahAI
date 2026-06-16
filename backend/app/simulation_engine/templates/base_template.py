from __future__ import annotations

import json
from typing import Any

from app.simulation_engine.schemas import SimulationSpecification


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>__TITLE__</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 12px;
  }
  #sim-container {
    max-width: 1100px;
    width: 100%;
    background: #1e293b;
    border-radius: 20px;
    border: 1px solid #334155;
    overflow: hidden;
    box-shadow: 0 25px 50px -12px rgba(0,0,0,0.6);
  }
  .sim-header {
    padding: 18px 24px 14px;
    border-bottom: 1px solid #334155;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  .sim-header h1 { font-size: 20px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.3px; }
  .sim-header .obj { font-size: 12px; color: #94a3b8; line-height: 1.5; margin-top: 2px; }
  .sim-header .sim-badge {
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
    padding: 4px 12px; border-radius: 20px; background: rgba(139,92,246,0.15);
    color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); white-space: nowrap;
  }
  .sim-body { display: flex; flex-direction: column; gap: 0; }
  @media (min-width: 820px) { .sim-body { flex-direction: row; } }
  .sim-visual {
    flex: 1; padding: 16px; display: flex; flex-direction: column;
    align-items: center; justify-content: center; min-height: 420px;
    background: #0f172a;
  }
  .sim-visual canvas {
    width: 100%; max-width: __CANVAS_WIDTH__px; height: auto;
    aspect-ratio: __CANVAS_WIDTH__ / __CANVAS_HEIGHT__;
    border-radius: 14px; border: 1px solid #334155;
    background: #f8fafc; touch-action: none; cursor: crosshair;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  }
  .sim-panel {
    width: 100%; max-width: 320px; padding: 16px 18px;
    border-left: 1px solid #334155;
    display: flex; flex-direction: column; gap: 10px;
    background: #162032;
  }
  @media (max-width: 819px) {
    .sim-panel { max-width: 100%; border-left: none; border-top: 1px solid #334155; }
    .sim-visual { min-height: 320px; }
  }
  .ctrl { display: flex; flex-direction: column; gap: 2px; }
  .ctrl-label {
    font-size: 11px; font-weight: 600; color: #94a3b8;
    display: flex; justify-content: space-between; align-items: center;
  }
  .ctrl-label .val-badge {
    background: rgba(139,92,246,0.15); color: #a78bfa;
    padding: 1px 8px; border-radius: 10px; font-size: 11px;
    font-family: 'Courier New', monospace; font-weight: 700;
    min-width: 40px; text-align: center;
  }
  input[type="range"] {
    width: 100%; height: 5px; -webkit-appearance: none; appearance: none;
    background: #334155; border-radius: 4px; outline: none; cursor: pointer;
    margin: 6px 0;
  }
  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none; width: 20px; height: 20px;
    border-radius: 50%; background: #8b5cf6;
    border: 3px solid #1e293b; cursor: pointer;
    box-shadow: 0 2px 8px rgba(139,92,246,0.4);
    transition: transform 0.1s;
  }
  input[type="range"]::-webkit-slider-thumb:hover { transform: scale(1.15); }
  input[type="range"]::-moz-range-thumb {
    width: 20px; height: 20px; border-radius: 50%;
    background: #8b5cf6; border: 3px solid #1e293b; cursor: pointer;
    box-shadow: 0 2px 8px rgba(139,92,246,0.4);
  }
  input[type="range"]:focus-visible { outline: 2px solid #a78bfa; outline-offset: 2px; }
  .ctrl-unit { font-size: 10px; color: #64748b; }
  .actions { display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
  .actions button {
    flex: 1; min-width: 60px; padding: 8px 12px; border: 1px solid #334155;
    border-radius: 8px; background: #1a2332; color: #e2e8f0;
    font-size: 11px; font-weight: 700; cursor: pointer;
    transition: all 0.12s; text-transform: uppercase; letter-spacing: 0.3px;
    display: flex; align-items: center; justify-content: center; gap: 4px;
  }
  .actions button:hover { background: #8b5cf6; border-color: #8b5cf6; color: #fff; }
  .actions button:active { transform: scale(0.97); }
  .actions button.primary { background: #8b5cf6; border-color: #8b5cf6; color: #fff; }
  .actions button.primary:hover { opacity: 0.88; }
  .actions button.green { background: #059669; border-color: #059669; }
  .actions button.green:hover { background: #047857; }
  .actions button.amber { background: #d97706; border-color: #d97706; }
  .actions button.amber:hover { background: #b45309; }
  .presets { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 2px; }
  .presets button {
    padding: 4px 10px; border: 1px solid #334155; border-radius: 6px;
    background: transparent; color: #94a3b8; font-size: 10px; font-weight: 600;
    cursor: pointer; transition: all 0.12s;
  }
  .presets button:hover { background: rgba(139,92,246,0.15); color: #a78bfa; border-color: #8b5cf6; }
  .values {
    display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 4px;
  }
  .vcard {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 10px; padding: 8px 10px; text-align: center;
    transition: border-color 0.2s;
  }
  .vcard:hover { border-color: #334155; }
  .vcard .lbl { font-size: 8px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; }
  .vcard .num {
    font-size: 18px; font-weight: 800; color: #a78bfa;
    font-family: 'Courier New', monospace; margin-top: 2px;
    transition: color 0.3s;
  }
  .graph-area { width: 100%; padding: 12px 16px 16px; border-top: 1px solid #334155; background: #0f172a; }
  .graph-area canvas {
    width: 100%; height: 180px; border-radius: 10px;
    border: 1px solid #1e293b; background: #f8fafc;
  }
  .graph-header {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;
  }
  .graph-header .gt { font-size: 12px; font-weight: 700; color: #cbd5e1; }
  .graph-header .gl {
    display: flex; gap: 12px; font-size: 10px; font-weight: 600;
  }
  .graph-header .gl span { display: flex; align-items: center; gap: 4px; }
  .graph-header .gl .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .assess-area { padding: 14px 24px; border-top: 1px solid #334155; background: #162032; }
  .assess-area .ql { font-size: 9px; font-weight: 700; color: #8b5cf6; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 6px; }
  .assess-area .q { font-size: 13px; line-height: 1.6; color: #e2e8f0; font-weight: 500; }
  .assess-area .h { font-size: 11px; color: #64748b; margin-top: 6px; font-style: italic; }
  .info-overlay {
    position: absolute; pointer-events: none; font-size: 12px;
    font-weight: 700; font-family: 'Courier New', monospace;
    color: #1e293b; background: rgba(255,255,255,0.9);
    padding: 6px 10px; border-radius: 8px; border: 1px solid #e2e8f0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: none;
  }
  @media (max-width: 480px) {
    body { padding: 6px; }
    .sim-header { padding: 12px 14px 10px; flex-direction: column; gap: 6px; }
    .sim-header h1 { font-size: 16px; }
    .sim-visual { padding: 8px; min-height: 240px; }
    .sim-panel { padding: 12px; }
    .values { grid-template-columns: 1fr; }
    .assess-area { padding: 10px 14px; }
    .graph-area { padding: 8px 10px 12px; }
  }
</style>
</head>
<body>
<div id="sim-container" role="application" aria-label="__TITLE__">
    <div class="sim-header" id="learning-objective">
      <div>
        <h1>__TITLE__</h1>
        <div class="obj">__OBJECTIVE__</div>
      </div>
      <span class="sim-badge">__SUBJECT_BADGE__</span>
    </div>
    <div class="sim-body">
      <div class="sim-visual" id="simulation-area" style="position:relative">
        <canvas id="canvas" width="__CANVAS_WIDTH__" height="__CANVAS_HEIGHT__"
                aria-label="Simulation canvas" role="img"></canvas>
        <div class="info-overlay" id="info-overlay"></div>
      </div>
      <div class="sim-panel" id="panel" role="toolbar" aria-label="Controls">
        __CONTROLS__
        <div class="actions">
          <button class="primary" id="play-btn" aria-label="Play/Pause">
            <span id="play-icon">II</span>
          </button>
          <button id="reset-btn" aria-label="Reset">↺</button>
          <button id="step-btn" aria-label="Step forward">▶|</button>
        </div>
        __SPEED_CONTROL__
        __PRESETS__
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

  class EventBus {
    constructor() { this._listeners = {}; }
    on(event, fn) { (this._listeners[event] ||= []).push(fn); return this; }
    off(event, fn) { const list = this._listeners[event]; if (list) this._listeners[event] = list.filter(f => f !== fn); return this; }
    emit(event, data) { (this._listeners[event] || []).forEach(fn => fn(data)); }
  }

  class StateManager {
    constructor(initial) {
      this._state = { ...initial };
      this._history = [];
      this._maxHistory = 500;
      this._bus = new EventBus();
    }
    get(key) { return this._state[key]; }
    set(key, value) {
      const old = this._state[key];
      if (old === value) return;
      this._state[key] = value;
      this._history.push({ key, old, new: value, time: performance.now() });
      if (this._history.length > this._maxHistory) this._history.shift();
      this._bus.emit('change:' + key, { key, old, new: value });
      this._bus.emit('change', { key, old, new: value });
    }
    getAll() { return { ...this._state }; }
    reset(initial) { this._state = { ...initial }; this._history = []; this._bus.emit('reset', this._state); }
    on(event, fn) { this._bus.on(event, fn); return this; }
  }

  class GraphManager {
    constructor(canvasId, config) {
      this.canvas = document.getElementById(canvasId);
      this.ctx = this.canvas.getContext('2d');
      this.config = config;
      this.data = {};
      this.maxPoints = 300;
      this.range = { xMin: 0, xMax: 10, yMin: 0, yMax: 10 };
      this.colors = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#06b6d4'];
    }
    pushData(seriesName, x, y) {
      if (!this.data[seriesName]) this.data[seriesName] = [];
      const arr = this.data[seriesName];
      arr.push({ x, y });
      if (arr.length > this.maxPoints) arr.shift();
    }
    clear() { this.data = {}; }
    setRange(xMin, xMax, yMin, yMax) {
      this.range = { xMin, xMax, yMin, yMax };
    }
    draw() {
      const ctx = this.ctx, c = this.canvas, w = c.width, h = c.height;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = '#f8fafc'; ctx.fillRect(0, 0, w, h);

      const pad = { t: 15, r: 20, b: 25, l: 45 };
      const pw = w - pad.l - pad.r;
      const ph = h - pad.t - pad.b;

      const xRange = this.range.xMax - this.range.xMin || 1;
      const yRange = this.range.yMax - this.range.yMin || 1;

      ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1;
      for (let i = 0; i <= 10; i++) {
        const x = pad.l + (i / 10) * pw;
        ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, pad.t + ph); ctx.stroke();
      }
      for (let i = 0; i <= 8; i++) {
        const y = pad.t + (i / 8) * ph;
        ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(pad.l + pw, y); ctx.stroke();
      }

      ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(pad.l, pad.t); ctx.lineTo(pad.l, pad.t + ph); ctx.lineTo(pad.l + pw, pad.t + ph); ctx.stroke();

      ctx.fillStyle = '#64748b'; ctx.font = '9px "Courier New", monospace'; ctx.textAlign = 'right';
      for (let i = 0; i <= 4; i++) {
        const yVal = this.range.yMin + (yRange * i) / 4;
        const yp = pad.t + ph - (i / 4) * ph;
        ctx.fillText(yVal.toFixed(1), pad.l - 5, yp + 3);
      }
      ctx.textAlign = 'center';
      for (let i = 0; i <= 4; i++) {
        const xVal = this.range.xMin + (xRange * i) / 4;
        const xp = pad.l + (i / 4) * pw;
        ctx.fillText(xVal.toFixed(1), xp, pad.t + ph + 14);
      }

      let colorIdx = 0;
      Object.entries(this.data).forEach(([name, points]) => {
        if (points.length < 2) return;
        const color = this.colors[colorIdx % this.colors.length];
        colorIdx++;
        ctx.strokeStyle = color; ctx.lineWidth = 2.5;
        ctx.beginPath();
        points.forEach((p, i) => {
          const x = pad.l + ((p.x - this.range.xMin) / xRange) * pw;
          const y = pad.t + ph - ((p.y - this.range.yMin) / yRange) * ph;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();

        const last = points[points.length - 1];
        if (last) {
          const lx = pad.l + ((last.x - this.range.xMin) / xRange) * pw;
          const ly = pad.t + ph - ((last.y - this.range.yMin) / yRange) * ph;
          ctx.fillStyle = color; ctx.beginPath(); ctx.arc(lx, ly, 3, 0, Math.PI * 2); ctx.fill();
        }
      });
    }
  }

  __CLASSES__

  function init() {
    const canvas = document.getElementById('canvas');
    const state = new StateManager(__INITIAL_STATE__);
    const bus = new EventBus();
    const graphCanvas = document.getElementById('graph-canvas');
    const graphMgr = graphCanvas ? new GraphManager('graph-canvas', __GRAPH_CONFIG__) : null;
    const engine = new SimulationEngine(canvas, state, bus);
    const renderer = new Renderer(canvas, state, bus);
    const controls = new ControlsManager(state, bus);
    const assessment = new AssessmentEngine(state, bus);

    window._engine = engine;
    let running = true;
    let lastTime = 0;
    let simSpeed = 1;
    let stepMode = false;

    function updateDisplayedValues() {
      const all = state.getAll();
      Object.entries(all).forEach(([key, val]) => {
        const el = document.getElementById('val-' + key);
        if (el) {
          if (typeof val === 'number') el.textContent = val.toFixed(el.dataset.precision || 2);
          else el.textContent = val;
        }
      });
      const hintEl = document.getElementById('hint-text');
      if (hintEl && engine.getHint) {
        hintEl.textContent = engine.getHint();
      }
    }

    function loop(time) {
      const dt = lastTime ? ((time - lastTime) / 1000) * simSpeed : 0.016;
      lastTime = time;
      if (running && !stepMode) {
        engine.update(dt, state);
        __GRAPH_DATA_PUSH__
        updateDisplayedValues();
        controls.syncLabels();
      }
      renderer.draw(dt, state);
      if (graphMgr) graphMgr.draw();
      bus.emit('render', { time, dt });
      if (stepMode) stepMode = false;
      requestAnimationFrame(loop);
    }

    document.getElementById('play-btn').addEventListener('click', function() {
      running = !running;
      document.getElementById('play-icon').textContent = running ? 'II' : '\\u25B6';
    });

    document.getElementById('reset-btn').addEventListener('click', function() {
      state.reset(__INITIAL_STATE__);
      if (graphMgr) { graphMgr.clear(); graphMgr.setRange(0, 10, 0, 10); }
      if (engine.onReset) engine.onReset();
      controls.sync();
      updateDisplayedValues();
      lastTime = 0;
    });

    const stepBtn = document.getElementById('step-btn');
    if (stepBtn) {
      stepBtn.addEventListener('click', function() {
        if (!running) {
          stepMode = true;
          running = true;
          setTimeout(function() {
            if (stepMode) { running = false; stepMode = false; }
          }, 50);
        }
      });
    }

    const speedSlider = document.getElementById('speed-slider');
    if (speedSlider) {
      speedSlider.addEventListener('input', function() {
        simSpeed = parseFloat(this.value);
        document.getElementById('speed-label').textContent = simSpeed.toFixed(1) + 'x';
      });
    }

    if (engine.canvasInteractions) {
      engine.canvasInteractions(canvas, state, bus);
    }

    controls.bind();
    updateDisplayedValues();
    requestAnimationFrame(loop);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
"""


def build_simulation_html(
    spec: SimulationSpecification,
    custom_script: str = "",
    custom_controls: str = "",
    custom_live_values: str = "",
    custom_graph: str = "",
    custom_assessment: str = "",
    custom_presets: str = "",
) -> str:
    title = spec.title
    objective = spec.learning_objectives[0] if spec.learning_objectives else f"Explore {spec.topic}"
    subject_badge = spec.subject.value.upper() if spec.subject else "SIMULATION"

    controls_html = custom_controls or _build_controls_html(spec)
    live_values_html = custom_live_values or _build_live_values_html(spec)
    graph_html = custom_graph or _build_graph_html(spec)
    assessment_html = custom_assessment or _build_assessment_html(spec)
    presets_html = custom_presets or _build_presets_html(spec)
    script_content = _build_script(spec, custom_script)

    speed_control = """  <div class="ctrl">
    <div class="ctrl-label">
      <span>Speed</span>
      <span class="val-badge" id="speed-label">1.0x</span>
    </div>
    <input type="range" id="speed-slider" min="0.1" max="3" step="0.1" value="1" aria-label="Simulation speed">
  </div>"""

    result = HTML_TEMPLATE
    result = result.replace("__TITLE__", title)
    result = result.replace("__OBJECTIVE__", objective)
    result = result.replace("__SUBJECT_BADGE__", subject_badge)
    result = result.replace("__CANVAS_WIDTH__", str(spec.canvas_width))
    result = result.replace("__CANVAS_HEIGHT__", str(spec.canvas_height))
    result = result.replace("__CONTROLS__", controls_html)
    result = result.replace("__LIVE_VALUES__", live_values_html)
    result = result.replace("__GRAPH__", graph_html)
    result = result.replace("__ASSESSMENT__", assessment_html)
    result = result.replace("__PRESETS__", presets_html)
    result = result.replace("__SPEED_CONTROL__", speed_control)
    result = result.replace("__SCRIPT__", script_content)

    return result


def _build_script(spec: SimulationSpecification, custom_script: str) -> str:
    if custom_script:
        classes_code = custom_script
    else:
        classes_code = _default_classes()

    initial_state = _build_initial_state(spec)
    spec_json = json.dumps(spec.raw_spec or spec.dict())

    graph_config_json = "{}"
    graph_data_push = ""
    if spec.graphs:
        g = spec.graphs[0]
        graph_config_json = json.dumps({"series": g.series})
        first_param_id = spec.parameters[0].id if spec.parameters else "param_1"
        series_name = g.series[0]["name"] if g.series else "Value"
        graph_data_push = f"""
if (graphMgr) {{
  const p1 = state.get('{first_param_id}') || 0;
  const p2 = state.get('output') || 0;
  graphMgr.pushData('{series_name}', p1, p2);
}}
"""

    script = CANVAS_BOILERPLATE
    script = script.replace("__SPEC__", spec_json)
    script = script.replace("__CLASSES__", classes_code)
    script = script.replace("__INITIAL_STATE__", json.dumps(initial_state))
    script = script.replace("__GRAPH_CONFIG__", graph_config_json)
    script = script.replace("__GRAPH_DATA_PUSH__", graph_data_push)

    return script


def _build_initial_state(spec: SimulationSpecification) -> dict:
    state = {}
    for p in spec.parameters:
        state[p.id] = p.default
    state["output"] = 0
    return state


def _default_classes() -> str:
    return """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
  }
  update(dt, state) {}
  onReset() {}
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
    ctx.fillStyle = '#1e293b';
    ctx.font = '14px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('Simulation Ready', w / 2, h / 2 - 10);
    ctx.font = '11px sans-serif'; ctx.fillStyle = '#64748b';
    ctx.fillText('Adjust controls to begin', w / 2, h / 2 + 14);
    ctx.textAlign = 'left';
  }
}

class ControlsManager {
  constructor(state, bus) {
    this.state = state; this.bus = bus; this.sliders = [];
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
        if (badge) badge.textContent = val.toFixed(1);
      });
    });
  }
  sync() {
    this.sliders.forEach(function(input) {
      const val = this.state.get(input.id);
      input.value = val;
    }, this);
  }
  syncLabels() {
    const all = this.state.getAll();
    this.sliders.forEach(function(input) {
      const val = all[input.id];
      if (val !== undefined) {
        const badge = document.getElementById('badge-' + input.id);
        if (badge) badge.textContent = typeof val === 'number' ? val.toFixed(1) : val;
      }
    });
  }
}

class AssessmentEngine {
  constructor(state, bus) { this.state = state; this.bus = bus; }
  getCurrentQuestion() { return document.getElementById('assess-q')?.textContent || ''; }
}
"""


def _build_controls_html(spec: SimulationSpecification) -> str:
    if not spec.parameters:
        return ""
    parts = []
    for p in spec.parameters:
        parts.append(_control_html(p.id, p.name, p.symbol, p.default, p.min, p.max, p.step, p.unit, p.description))
    return "\n".join(parts)


def _control_html(
    cid: str, name: str, symbol: str, default: float,
    min_v: float, max_v: float, step: float, unit: str, desc: str,
) -> str:
    parts = []
    parts.append('    <div class="ctrl">')
    parts.append(f'      <div class="ctrl-label">')
    parts.append(f'        <span>{name} ({symbol}) <span class="ctrl-unit">{unit}</span></span>')
    parts.append(f'        <span class="val-badge" id="badge-{cid}">{default}</span>')
    parts.append(f'      </div>')
    parts.append(f'      <input type="range" id="{cid}" min="{min_v}" max="{max_v}" step="{step}" value="{default}"')
    parts.append(f'             aria-label="{name}: {desc}" title="{desc}">')
    parts.append('    </div>')
    return "\n".join(parts)


def _build_live_values_html(spec: SimulationSpecification) -> str:
    params = spec.parameters
    if not params:
        return ""
    parts = []
    colors = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#8b5cf6']
    for i, p in enumerate(params[:6]):
        color = colors[i % len(colors)]
        parts.append(_value_card_html(p.symbol, p.id, p.default, color))
    if spec.equations:
        parts.append(_value_card_html("Output", "output", 0, "#06b6d4"))
    return "\n".join(parts)


def _value_card_html(label: str, vid: str, default_val: float, color: str | None = None) -> str:
    style = f' style="color:{color}"' if color else ""
    return f'    <div class="vcard">\n      <div class="lbl">{label}</div>\n      <div class="num" id="val-{vid}"{style}>{default_val}</div>\n    </div>'


def _build_graph_html(spec: SimulationSpecification) -> str:
    if not spec.graphs:
        return ""
    g = spec.graphs[0]
    legend_items = "".join(
        f'<span><span class="dot" style="background:{s.get("color","#6366f1")}"></span>{s["name"]}</span>'
        for s in g.series
    )
    return f'''  <div class="graph-area">
    <div class="graph-header">
      <div class="gt">{g.title}</div>
      <div class="gl">{legend_items}</div>
    </div>
    <canvas id="graph-canvas" width="700" height="180" aria-label="{g.title} graph"></canvas>
  </div>'''


def _build_assessment_html(spec: SimulationSpecification) -> str:
    if not spec.assessment_prompts:
        return ""
    ap = spec.assessment_prompts[0]
    return f'''  <div class="assess-area" id="assess-area">
    <div class="ql">{"Try This"}</div>
    <div class="q" id="assess-q">{ap.question}</div>
    <div class="h" id="assess-h">{ap.hint}</div>
  </div>'''


def _build_presets_html(spec: SimulationSpecification) -> str:
    return ""
