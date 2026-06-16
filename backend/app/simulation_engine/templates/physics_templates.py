from __future__ import annotations

from app.simulation_engine.schemas import SimulationSpecification, SimulationType
from app.simulation_engine.templates.base_template import build_simulation_html
import json


PROJECTILE_MOTION_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas;
    this.state = state;
    this.bus = bus;
    this.trail = [];
    this.maxTrail = 500;
    this.time = 0;
    this.px = 60; this.py = 0;
    this.vx = 0; this.vy = 0;
    this.launched = false;
    this.readyToLaunch = true;
    this.groundY = 0;
  }

  update(dt, state) {
    const g = state.get('gravity') || 9.81;
    const angle = state.get('angle') || 45;
    const speed = state.get('initial_velocity') || 20;
    const h = this.canvas.height;
    this.groundY = h - 30;

    if (!this.launched && this.readyToLaunch) {
      const angleRad = angle * Math.PI / 180;
      this.vx = speed * Math.cos(angleRad) * 8;
      this.vy = -speed * Math.sin(angleRad) * 8;
      this.px = 60;
      this.py = this.groundY;
      this.trail = [];
      this.time = 0;
      this.launched = true;
      this.readyToLaunch = false;
      state.set('in_flight', true);
    }

    if (this.launched) {
      this.time += dt;
      this.px += this.vx * dt;
      this.vy += g * 40 * dt;
      this.py += this.vy * dt;

      if (this.py >= this.groundY) {
        this.py = this.groundY;
        this.vy = 0; this.vx = 0;
        this.launched = false;
        state.set('in_flight', false);
      }

      const sx = this.px;
      const sy = this.py;
      state.set('pos_x', parseFloat((this.px / 8).toFixed(1)));
      state.set('pos_y', parseFloat(((this.groundY - this.py) / 8).toFixed(1)));
      state.set('vel_x', parseFloat((this.vx / 8).toFixed(1)));
      state.set('vel_y', parseFloat((-this.vy / 8).toFixed(1)));
      state.set('time_of_flight', parseFloat(this.time.toFixed(2)));
      state.set('speed', parseFloat(Math.sqrt(this.vx*this.vx + this.vy*this.vy).toFixed(1)));

      this.trail.push({ x: sx, y: sy });
      if (this.trail.length > this.maxTrail) this.trail.shift();

      const range = (this.px - 60) / 8;
      state.set('range', parseFloat(range.toFixed(1)));
      const maxH = this._maxHeight;
      if (this.py < this._minY || this._minY === undefined) {
        this._minY = this.py;
        state.set('max_height', parseFloat(((this.groundY - this.py) / 8).toFixed(1)));
      }
    }
  }

  onReset() {
    this.trail = [];
    this.launched = false;
    this.readyToLaunch = true;
    this.time = 0;
    this._minY = undefined;
    this.px = 60; this.py = 0;
  }

  canvasInteractions(canvas, state, bus) {
    const self = this;
    canvas.addEventListener('click', function(e) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const cx = (e.clientX - rect.left) * scaleX;
      const cy = (e.clientY - rect.top) * scaleX;
      const angle = Math.atan2(-(cy - self.groundY), cx - 60) * 180 / Math.PI;
      if (angle > 5 && angle < 85) {
        state.set('angle', Math.round(angle));
        document.getElementById('badge-angle').textContent = Math.round(angle);
        document.getElementById('angle').value = Math.round(angle);
      }
    });
  }

  getHint() {
    if (!this.launched) return 'Adjust angle/speed, then click Launch';
    if (this.launched) return 'Watch the trajectory - drag on canvas to set angle';
    return '';
  }
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

    const groundY = h - 30;

    ctx.fillStyle = '#e2e8f0'; ctx.fillRect(0, groundY + 2, w, h - groundY);

    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, groundY); ctx.lineTo(w, groundY); ctx.stroke();

    ctx.fillStyle = '#cbd5e1'; ctx.font = '9px sans-serif';
    ctx.fillText('GROUND', w - 60, groundY - 4);

    const gridStep = 40;
    ctx.strokeStyle = '#f1f5f9'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += gridStep) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, groundY); ctx.stroke();
    }

    const engine = window._engine;

    if (engine && engine.trail.length > 1) {
      const gradient = ctx.createLinearGradient(60, 0, w, 0);
      gradient.addColorStop(0, '#6366f1');
      gradient.addColorStop(0.5, '#8b5cf6');
      gradient.addColorStop(1, '#ec4899');
      ctx.strokeStyle = gradient; ctx.lineWidth = 2.5;
      ctx.beginPath();
      let prevX, prevY;
      engine.trail.forEach((p, i) => {
        if (i === 0) { ctx.moveTo(p.x, p.y); prevX = p.x; prevY = p.y; }
        else { ctx.lineTo(p.x, p.y); }
      });
      ctx.stroke();

      if (engine.trail.length > 1) {
        const last = engine.trail[engine.trail.length - 1];
        ctx.fillStyle = '#ec4899';
        ctx.beginPath(); ctx.arc(last.x, last.y, 4, 0, Math.PI * 2); ctx.fill();
      }
    }

    if (engine) {
      const px = engine.px, py = engine.py;
      const angle = state.get('angle') || 45;
      const speed = state.get('initial_velocity') || 20;

      ctx.save();
      if (engine.launched || engine.trail.length === 0) {
        ctx.shadowBlur = 20; ctx.shadowColor = '#6366f1';
      }
      const gradient2 = ctx.createRadialGradient(px - 3, py - 3, 2, px, py, 12);
      gradient2.addColorStop(0, '#a78bfa');
      gradient2.addColorStop(1, '#6366f1');
      ctx.fillStyle = gradient2;
      ctx.beginPath(); ctx.arc(px, py, 10, 0, Math.PI * 2); ctx.fill();
      ctx.restore();

      if (!engine.launched && engine.trail.length === 0) {
        const angleRad = angle * Math.PI / 180;
        const arrowLen = Math.min(60, speed * 3);

        ctx.strokeStyle = '#6366f1'; ctx.lineWidth = 2.5;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(px + arrowLen * Math.cos(angleRad), py - arrowLen * Math.sin(angleRad));
        ctx.stroke(); ctx.setLineDash([]);

        ctx.fillStyle = '#6366f1'; ctx.font = '11px sans-serif';
        ctx.fillText(speed + ' m/s', px + arrowLen * Math.cos(angleRad) + 5, py - arrowLen * Math.sin(angleRad));

        ctx.fillStyle = '#f59e0b';
        ctx.beginPath();
        ctx.arc(px + 25, py - 8, 3, 0, Math.PI * 2); ctx.fill();
        ctx.font = '10px sans-serif';
        ctx.fillText(angle + '\\u00B0', px + 32, py - 4);
      }

      if (engine.launched) {
        const vx = state.get('vel_x') || 0;
        const vy = state.get('vel_y') || 0;
        const s = state.get('speed') || 0;
        const scale = 0.4;
        ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px + vx * scale, py + vy * scale); ctx.stroke();

        ctx.fillStyle = '#ef4444'; ctx.font = '9px sans-serif';
        ctx.fillText('v=' + s, px + vx * scale + 4, py + vy * scale);
      }

      ctx.fillStyle = '#1e293b';
      ctx.font = 'bold 12px "Courier New", monospace';
      ctx.fillText('Pos: (' + (state.get('pos_x') || 0) + ', ' + (state.get('pos_y') || 0) + ') m', 10, 18);
      ctx.fillStyle = '#475569';
      ctx.font = '11px "Courier New", monospace';
      ctx.fillText('Time: ' + (state.get('time_of_flight') || '0.00') + ' s', 10, 36);
      ctx.fillStyle = '#6366f1';
      ctx.fillText('Range: ' + (state.get('range') || '0.0') + ' m', 10, 54);

      if (!engine.launched && engine.trail.length === 0) {
        ctx.fillStyle = '#94a3b8';
        ctx.font = '13px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText('Click Launch or tap canvas to set angle', w / 2, h / 2 - 30);
        ctx.textAlign = 'left';
      }
    }
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
        const engine = window._engine;
        if (engine && !engine.launched) {
          engine.readyToLaunch = true;
          engine.trail = [];
          engine._minY = undefined;
          engine.px = 60; engine.py = 0;
        }
      });
    });
    const launchBtn = document.getElementById('launch-btn');
    if (launchBtn) {
      launchBtn.addEventListener('click', function() {
        const engine = window._engine;
        if (engine) {
          engine.launched = false;
          engine.readyToLaunch = true;
          engine.trail = [];
          engine._minY = undefined;
        }
      });
    }
  }
  sync() {
    this.sliders.forEach(function(input) {
      const val = this.state.get(input.id);
      if (val !== undefined) input.value = val;
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


def build_physics_simulation(spec: SimulationSpecification) -> str:
    sim_type = spec.simulation_type.value

    if sim_type == "projectile_motion":
        return _build_projectile_motion(spec)
    elif sim_type == "electricity":
        return _build_electricity(spec)
    elif sim_type == "waves":
        return _build_waves(spec)
    elif sim_type == "forces":
        return _build_forces(spec)
    elif sim_type == "energy":
        return _build_energy(spec)
    elif sim_type == "buoyancy":
        return _build_buoyancy(spec)
    else:
        return build_simulation_html(spec, custom_script=_build_generic_physics(spec))


def _build_projectile_motion(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Launch Angle (&theta;) <span class="ctrl-unit">deg</span></span>
        <span class="val-badge" id="badge-angle">45</span>
      </div>
      <input type="range" id="angle" min="0" max="90" step="1" value="45" aria-label="Launch angle" title="Angle above horizontal">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Initial Speed (v) <span class="ctrl-unit">m/s</span></span>
        <span class="val-badge" id="badge-initial_velocity">20</span>
      </div>
      <input type="range" id="initial_velocity" min="5" max="50" step="1" value="20" aria-label="Initial velocity" title="Launch speed">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Gravity (g) <span class="ctrl-unit">m/s&sup2;</span></span>
        <span class="val-badge" id="badge-gravity">9.81</span>
      </div>
      <input type="range" id="gravity" min="0.1" max="30" step="0.1" value="9.81" aria-label="Gravity" title="Gravitational acceleration">
    </div>"""

    presets = """  <div class="presets">
    <span style="font-size:9px;color:#64748b;font-weight:600;padding-right:4px">Presets:</span>
    <button data-angle="45" data-speed="20" data-gravity="9.81">Standard</button>
    <button data-angle="30" data-speed="25" data-gravity="9.81">Long Range</button>
    <button data-angle="75" data-speed="15" data-gravity="9.81">High Arc</button>
    <button data-angle="45" data-speed="20" data-gravity="1.62">Moon</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var angle = this.getAttribute('data-angle');
        var speed = this.getAttribute('data-speed');
        var gravity = this.getAttribute('data-gravity');
        document.getElementById('angle').value = angle;
        document.getElementById('initial_velocity').value = speed;
        document.getElementById('gravity').value = gravity;
        document.getElementById('badge-angle').textContent = angle;
        document.getElementById('badge-initial_velocity').textContent = speed;
        document.getElementById('badge-gravity').textContent = gravity;
        state.set('angle', parseFloat(angle));
        state.set('initial_velocity', parseFloat(speed));
        state.set('gravity', parseFloat(gravity));
        var engine = window._engine;
        if (engine && !engine.launched) {
          engine.readyToLaunch = true; engine.trail = []; engine._minY = undefined;
          engine.px = 60; engine.py = 0;
        }
      });
    });
"""

    script = PROJECTILE_MOTION_ENGINE.replace(
        "class ControlsManager {",
        presets_script + "\n\nclass ControlsManager {"
    )

    values = """    <div class="vcard"><div class="lbl">X Position</div><div class="num" id="val-pos_x" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Y Position</div><div class="num" id="val-pos_y" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">Time</div><div class="num" id="val-time_of_flight" style="color:#f59e0b">0</div></div>
    <div class="vcard"><div class="lbl">Range</div><div class="num" id="val-range" style="color:#ec4899">0</div></div>
    <div class="vcard"><div class="lbl">Speed</div><div class="num" id="val-speed" style="color:#06b6d4">0</div></div>
    <div class="vcard"><div class="lbl">Max Height</div><div class="num" id="val-max_height" style="color:#8b5cf6">0</div></div>"""

    graph = """  <div class="graph-area">
    <div class="graph-header">
      <div class="gt">Height vs. Distance</div>
      <div class="gl"><span><span class="dot" style="background:#6366f1"></span>Trajectory</span></div>
    </div>
    <canvas id="graph-canvas" width="700" height="180" aria-label="Projectile trajectory graph"></canvas>
  </div>"""

    graph_data_push = """
if (graphMgr && state.get('in_flight')) {
  graphMgr.setRange(0, 80, 0, 45);
  graphMgr.pushData('Trajectory', parseFloat(state.get('pos_x')), parseFloat(state.get('pos_y')));
}
"""

    script = script.replace(
        "__GRAPH_DATA_PUSH_PLACEHOLDER__",
        "// Projectile: graphMgr handled in base template"
    )

    html = build_simulation_html(
        spec,
        custom_script=script,
        custom_controls=controls,
        custom_live_values=values,
        custom_graph=graph,
        custom_assessment=_build_assessment(spec),
        custom_presets=presets,
    )

    html = html.replace(
        "graphMgr.pushData",
        "graphMgr && graphMgr.setRange(0, 80, 0, 45);\n    graphMgr.pushData"
    )

    return html


def _build_electricity(spec: SimulationSpecification) -> str:
    script = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.particles = []; this.time = 0;
    for (let i = 0; i < 30; i++) {
      this.particles.push({ x: Math.random(), y: 0.2 + Math.random() * 0.6, active: true });
    }
  }
  update(dt, state) {
    this.time += dt;
    const V = state.get('voltage') || 5;
    const R = state.get('resistance') || 10;
    const I = V / R;
    state.set('current', parseFloat(I.toFixed(3)));
    state.set('power', parseFloat((V * I).toFixed(2)));
    const speed = I * 0.6;
    this.particles.forEach(function(p) {
      p.x += speed * dt;
      if (p.x > 1) p.x = 0;
    });
  }
  onReset() { this.time = 0; }
  canvasInteractions(canvas, state, bus) {
    var self = this;
    var dragging = false;
    function getResistanceFromY(clientY) {
      var rect = canvas.getBoundingClientRect();
      var scaleY = canvas.height / rect.height;
      var cy = (clientY - rect.top) * scaleY;
      var r = 5 + (cy / canvas.height) * 95;
      return Math.round(Math.min(100, Math.max(5, r)));
    }
    canvas.addEventListener('mousedown', function(e) {
      dragging = true;
      state.set('resistance', getResistanceFromY(e.clientY));
    });
    canvas.addEventListener('mousemove', function(e) {
      if (dragging) {
        state.set('resistance', getResistanceFromY(e.clientY));
      }
    });
    canvas.addEventListener('mouseup', function() { dragging = false; });
    canvas.addEventListener('touchstart', function(e) {
      e.preventDefault();
      state.set('resistance', getResistanceFromY(e.touches[0].clientY));
    });
    canvas.addEventListener('touchmove', function(e) {
      e.preventDefault();
      state.set('resistance', getResistanceFromY(e.touches[0].clientY));
    });
  }
  getHint() { return 'Drag up/down on resistor to change value'; }
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

    const V = state.get('voltage') || 5;
    const R = state.get('resistance') || 10;
    const I = V / R;

    ctx.strokeStyle = '#cbd5e1'; ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(70, 70); ctx.lineTo(250, 70);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(70, 190); ctx.lineTo(250, 190);
    ctx.stroke();

    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(250, 70); ctx.lineTo(250, 80);
    ctx.stroke();

    var resH = Math.min(120, Math.max(30, R * 1.2));
    var resY = 70 + (190 - 70 - resH) / 2;

    ctx.fillStyle = '#ef4444';
    ctx.shadowBlur = 10; ctx.shadowColor = 'rgba(239,68,68,0.3)';
    ctx.beginPath();
    ctx.moveTo(250, resY); ctx.lineTo(265, resY);
    ctx.lineTo(265, resY + resH * 0.25); ctx.lineTo(235, resY + resH * 0.25);
    ctx.lineTo(265, resY + resH * 0.5); ctx.lineTo(235, resY + resH * 0.5);
    ctx.lineTo(265, resY + resH * 0.75); ctx.lineTo(235, resY + resH * 0.75);
    ctx.lineTo(250, resY + resH); ctx.lineTo(265, resY + resH);
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#fff'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(R + '\\u03A9', 250, resY + resH / 2 + 3);

    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(250, resY + resH); ctx.lineTo(250, 190);
    ctx.stroke();

    ctx.fillStyle = '#22c55e';
    ctx.shadowBlur = 12; ctx.shadowColor = 'rgba(34,197,94,0.3)';
    ctx.fillRect(40, 95, 50, 60);
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#fff'; ctx.font = 'bold 10px sans-serif';
    ctx.fillText(V + 'V', 48, 130);
    ctx.fillStyle = '#1e293b'; ctx.font = '9px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('BATTERY', 65, 170);

    var engine = window._engine;
    if (engine) {
      engine.particles.forEach(function(p) {
        var px = 90 + p.x * 160;
        var py = 70 + p.y * 120;
        ctx.fillStyle = '#6366f1';
        ctx.beginPath(); ctx.arc(px, py, 3, 0, Math.PI * 2); ctx.fill();
        if (p.x > 0.95) {
          ctx.fillStyle = '#fbbf24';
          ctx.beginPath(); ctx.arc(px, py, 2, 0, Math.PI * 2); ctx.fill();
        }
      });
    }

    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 13px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('I = ' + I.toFixed(3) + ' A', 10, 22);
    ctx.fillStyle = '#475569'; ctx.font = '11px "Courier New", monospace';
    ctx.fillText('V = ' + V.toFixed(1) + ' V   R = ' + R.toFixed(0) + ' \\u03A9', 10, 40);
    ctx.fillStyle = '#6366f1';
    ctx.fillText('P = ' + (V * I).toFixed(2) + ' W', 10, 58);

    ctx.fillStyle = '#94a3b8'; ctx.font = '9px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('Drag resistor to change value', w - 10, h - 8);
  }
}

class ControlsManager {
  constructor(state, bus) { this.state = state; this.bus = bus; this.sliders = []; }
  bind() {
    var self = this;
    document.querySelectorAll('input[type="range"]').forEach(function(input) {
      if (input.id === 'speed-slider') return;
      var key = input.id; self.sliders.push(input);
      self.state.set(key, parseFloat(input.value));
      input.addEventListener('input', function() {
        var val = parseFloat(this.value);
        self.state.set(key, val);
        var badge = document.getElementById('badge-' + key);
        if (badge) badge.textContent = val.toFixed(1);
      });
    });
  }
  sync() { this.sliders.forEach(function(input) { var val = this.state.get(input.id); if (val !== undefined) input.value = val; }, this); }
  syncLabels() {
    var all = this.state.getAll();
    this.sliders.forEach(function(input) {
      var val = all[input.id]; if (val !== undefined) {
        var badge = document.getElementById('badge-' + input.id);
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

    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Voltage (V) <span class="ctrl-unit">V</span></span>
        <span class="val-badge" id="badge-voltage">5.0</span>
      </div>
      <input type="range" id="voltage" min="1" max="24" step="0.5" value="5" aria-label="Voltage" title="Battery voltage">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Resistance (R) <span class="ctrl-unit">&Omega;</span></span>
        <span class="val-badge" id="badge-resistance">10</span>
      </div>
      <input type="range" id="resistance" min="5" max="100" step="1" value="10" aria-label="Resistance" title="Circuit resistance">
    </div>"""

    values = """    <div class="vcard"><div class="lbl">Current (I)</div><div class="num" id="val-current" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Power (P)</div><div class="num" id="val-power" style="color:#ec4899">0</div></div>
    <div class="vcard"><div class="lbl">Voltage</div><div class="num" id="val-voltage" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">Resistance</div><div class="num" id="val-resistance" style="color:#f59e0b">0</div></div>"""

    return build_simulation_html(spec, custom_script=script, custom_controls=controls, custom_live_values=values, custom_assessment=_build_assessment(spec))


def _build_waves(spec: SimulationSpecification) -> str:
    script = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.time = 0;
  }
  update(dt, state) {
    this.time += dt;
    var freq = state.get('frequency') || 2;
    var amp = state.get('amplitude') || 50;
    var speed = state.get('speed') || 60;
    var sup = state.get('superposition') || 0;
    var w = this.canvas.width;
    var points1 = [], points2 = [], pointsR = [];
    for (var x = 0; x <= w; x += 3) {
      var t = this.time;
      var k = freq * 0.02;
      var w1 = amp * Math.sin(k * x - speed * 0.03 * t);
      var y1 = w1;
      var y2 = 0;
      if (sup > 0) {
        y2 = amp * 0.6 * Math.sin(k * x * 0.7 - speed * 0.04 * t + sup * 2);
      }
      points1.push({ x: x, y: y1 });
      points2.push({ x: x, y: y2 });
      pointsR.push({ x: x, y: y1 + y2 });
    }
    state.set('wave1', points1);
    state.set('wave2', points2);
    state.set('wave_result', pointsR);
  }
  onReset() { this.time = 0; }
  getHint() { return 'Adjust superposition to see wave interference'; }
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

    var cy = h / 2;
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1;
    ctx.setLineDash([6, 4]);
    ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(w, cy); ctx.stroke();
    ctx.setLineDash([]);

    var sup = state.get('superposition') || 0;

    function drawWave(points, color, lineWidth) {
      if (!points || points.length < 2) return;
      ctx.strokeStyle = color; ctx.lineWidth = lineWidth || 2;
      ctx.beginPath();
      points.forEach(function(p, i) {
        var y = cy - p.y;
        if (i === 0) ctx.moveTo(p.x, y); else ctx.lineTo(p.x, y);
      });
      ctx.stroke();
    }

    if (sup > 0) {
      drawWave(state.get('wave2'), '#cbd5e1', 1.5);
    }

    var result = state.get('wave_result');
    if (result && sup > 0.3) {
      drawWave(result, '#ef4444', 3);
    }

    drawWave(state.get('wave1'), '#6366f1', 2.5);

    var amp = state.get('amplitude') || 50;
    var freq = state.get('frequency') || 2;
    var speed = state.get('speed') || 60;
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('f = ' + freq.toFixed(1) + ' Hz', 10, 18);
    ctx.fillStyle = '#475569'; ctx.font = '11px "Courier New", monospace';
    ctx.fillText('A = ' + amp.toFixed(1) + '  v = ' + speed.toFixed(0), 10, 36);

    var labels = [];
    labels.push({ text: 'Wave 1', color: '#6366f1' });
    if (sup > 0) { labels.push({ text: 'Wave 2', color: '#cbd5e1' }); }
    if (sup > 0.3) { labels.push({ text: 'Result', color: '#ef4444' }); }
    labels.forEach(function(l, i) {
      ctx.fillStyle = l.color; ctx.font = '9px sans-serif';
      ctx.fillText(l.text, w - 100, 18 + i * 14);
    });

    ctx.fillStyle = '#94a3b8'; ctx.font = '9px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('Drag on wave to change frequency', w - 10, h - 8);
  }
}

class ControlsManager {
  constructor(state, bus) { this.state = state; this.bus = bus; this.sliders = []; }
  bind() {
    var self = this;
    document.querySelectorAll('input[type="range"]').forEach(function(input) {
      if (input.id === 'speed-slider') return;
      var key = input.id; self.sliders.push(input);
      self.state.set(key, parseFloat(input.value));
      input.addEventListener('input', function() {
        var val = parseFloat(this.value);
        self.state.set(key, val);
        var badge = document.getElementById('badge-' + key);
        if (badge) badge.textContent = val.toFixed(1);
      });
    });
  }
  sync() { this.sliders.forEach(function(input) { var val = this.state.get(input.id); if (val !== undefined) input.value = val; }, this); }
  syncLabels() {
    var all = this.state.getAll();
    this.sliders.forEach(function(input) {
      var val = all[input.id]; if (val !== undefined) {
        var badge = document.getElementById('badge-' + input.id);
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

    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Frequency (f) <span class="ctrl-unit">Hz</span></span>
        <span class="val-badge" id="badge-frequency">2.0</span>
      </div>
      <input type="range" id="frequency" min="0.5" max="10" step="0.1" value="2" aria-label="Frequency">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Amplitude (A) <span class="ctrl-unit">px</span></span>
        <span class="val-badge" id="badge-amplitude">50</span>
      </div>
      <input type="range" id="amplitude" min="10" max="120" step="1" value="50" aria-label="Amplitude">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Wave Speed (v) <span class="ctrl-unit">px/s</span></span>
        <span class="val-badge" id="badge-speed">60</span>
      </div>
      <input type="range" id="speed" min="10" max="150" step="1" value="60" aria-label="Wave speed">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Superposition <span class="ctrl-unit"></span></span>
        <span class="val-badge" id="badge-superposition">0.0</span>
      </div>
      <input type="range" id="superposition" min="0" max="1" step="0.05" value="0" aria-label="Superposition mixing">
    </div>"""

    values = """    <div class="vcard"><div class="lbl">Wavelength</div><div class="num" id="val-wavelength" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Period</div><div class="num" id="val-period" style="color:#10b981">0</div></div>"""

    graph_html = """  <div class="graph-area">
    <div class="graph-header">
      <div class="gt">Wave Displacement</div>
      <div class="gl"><span><span class="dot" style="background:#6366f1"></span>Wave 1</span><span><span class="dot" style="background:#ef4444"></span>Resultant</span></div>
    </div>
    <canvas id="graph-canvas" width="700" height="180"></canvas>
  </div>"""

    return build_simulation_html(spec, custom_script=script, custom_controls=controls, custom_live_values=values, custom_graph=graph_html, custom_assessment=_build_assessment(spec))


def _build_forces(spec: SimulationSpecification) -> str:
    script = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.pos = 80; this.vel = 0; this.time = 0;
  }
  update(dt, state) {
    this.time += dt;
    var mass = state.get('mass') || 5;
    var applied = state.get('applied_force') || 20;
    var friction = state.get('friction') || 0.2;
    var g = 9.81;
    var normal = mass * g;
    var fApplied = applied;
    var fFriction = Math.min(friction * normal, Math.abs(fApplied) > 0.1 ? Math.abs(fApplied) : 0);
    if (Math.abs(this.vel) < 0.01) fFriction = Math.min(fFriction, Math.abs(fApplied));
    if (fApplied < 0.1) { fFriction = friction * normal * (this.vel > 0 ? -1 : this.vel < 0 ? 1 : 0); }
    var net = fApplied - (this.vel > 0.01 ? fFriction : this.vel < -0.01 ? -fFriction : fApplied > fFriction ? fFriction : fApplied);
    if (Math.abs(fApplied) < 0.5 && Math.abs(this.vel) < 0.05) net = 0;
    var accel = net / mass;
    this.vel += accel * dt;
    this.pos += this.vel * dt * 5;
    if (this.pos > this.canvas.width - 40) { this.pos = this.canvas.width - 40; this.vel = 0; }
    if (this.pos < 40) { this.pos = 40; this.vel = 0; }
    state.set('net_force', parseFloat(net.toFixed(1)));
    state.set('acceleration', parseFloat(accel.toFixed(2)));
    state.set('velocity', parseFloat(this.vel.toFixed(2)));
    state.set('friction_force', parseFloat(fFriction.toFixed(1)));
    state.set('normal_force', parseFloat(normal.toFixed(1)));
    state.set('weight', parseFloat((mass * g).toFixed(1)));
    state.set('block_x', this.pos);
  }
  onReset() { this.pos = 80; this.vel = 0; this.time = 0; }
  canvasInteractions(canvas, state, bus) {
    var self = this;
    canvas.addEventListener('click', function(e) {
      var rect = canvas.getBoundingClientRect();
      var scaleX = canvas.width / rect.width;
      var cx = (e.clientX - rect.left) * scaleX;
      var force = ((cx - 40) / (canvas.width - 80)) * 80;
      force = Math.max(-40, Math.min(80, force));
      state.set('applied_force', Math.round(force));
      document.getElementById('badge-applied_force').textContent = Math.round(force);
      document.getElementById('applied_force').value = Math.round(force);
    });
  }
  getHint() { return 'Click on canvas to set applied force direction & magnitude'; }
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

    var blockY = h - 80;
    var bx = state.get('block_x') || 80;

    ctx.fillStyle = '#e2e8f0'; ctx.fillRect(0, h - 50, w, 50);
    ctx.strokeStyle = '#cbd5e1'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(0, h - 50); ctx.lineTo(w, h - 50); ctx.stroke();

    ctx.shadowBlur = 12; ctx.shadowColor = 'rgba(99,102,241,0.3)';
    ctx.fillStyle = '#6366f1';
    ctx.beginPath();
    var r = 22;
    ctx.roundRect(bx - r, blockY - r, r * 2, r * 2, 4);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#fff'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText((state.get('mass') || 5) + 'kg', bx, blockY + 3);

    var scale = 0.5;
    var applied = state.get('applied_force') || 0;
    var friction = state.get('friction_force') || 0;
    var net = state.get('net_force') || 0;
    var normal = state.get('normal_force') || 0;
    var weight = state.get('weight') || 0;

    if (Math.abs(applied) > 0.5) {
      ctx.strokeStyle = '#22c55e'; ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(bx, blockY);
      ctx.lineTo(bx + applied * scale, blockY);
      ctx.stroke();
      var dir = applied > 0 ? 1 : -1;
      ctx.fillStyle = '#22c55e';
      ctx.beginPath();
      ctx.moveTo(bx + applied * scale, blockY - 5);
      ctx.lineTo(bx + applied * scale + dir * 10, blockY);
      ctx.lineTo(bx + applied * scale, blockY + 5);
      ctx.fill();
      ctx.fillStyle = '#22c55e'; ctx.font = '9px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText('F_app=' + applied.toFixed(0) + 'N', bx + applied * scale * 0.5, blockY - 15);
    }

    if (friction > 0.5 && Math.abs(state.get('velocity') || 0) > 0.01) {
      ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(bx, blockY);
      ctx.lineTo(bx - friction * scale * 0.5, blockY);
      ctx.stroke();
      ctx.fillStyle = '#ef4444'; ctx.font = '9px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText('F_fric=' + friction.toFixed(0) + 'N', bx - friction * scale * 0.25, blockY + 20);
    }

    ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 2;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(bx - 30, blockY - r - 2);
    ctx.lineTo(bx + 30, blockY - r - 2);
    ctx.stroke();
    ctx.fillStyle = '#f59e0b'; ctx.font = '8px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('N=' + normal.toFixed(0) + 'N', bx, blockY - r - 6);
    ctx.setLineDash([]);

    ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(bx - 30, blockY + r + 2);
    ctx.lineTo(bx + 30, blockY + r + 2);
    ctx.stroke();
    ctx.fillStyle = '#f59e0b'; ctx.font = '8px sans-serif';
    ctx.fillText('W=' + weight.toFixed(0) + 'N', bx, blockY + r + 16);

    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('Net Force: ' + net.toFixed(1) + ' N', 10, 18);
    ctx.fillStyle = '#475569'; ctx.font = '11px "Courier New", monospace';
    ctx.fillText('a = ' + (state.get('acceleration') || 0).toFixed(2) + ' m/s' + String.fromCharCode(178), 10, 36);
    ctx.fillStyle = '#6366f1';
    ctx.fillText('v = ' + (state.get('velocity') || 0).toFixed(2) + ' m/s', 10, 54);

    ctx.fillStyle = '#94a3b8'; ctx.font = '9px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('Click canvas to set force direction', w - 10, h - 8);
  }
}

class ControlsManager {
  constructor(state, bus) { this.state = state; this.bus = bus; this.sliders = []; }
  bind() {
    var self = this;
    document.querySelectorAll('input[type="range"]').forEach(function(input) {
      if (input.id === 'speed-slider') return;
      var key = input.id; self.sliders.push(input);
      self.state.set(key, parseFloat(input.value));
      input.addEventListener('input', function() {
        var val = parseFloat(this.value);
        self.state.set(key, val);
        var badge = document.getElementById('badge-' + key);
        if (badge) badge.textContent = val.toFixed(1);
      });
    });
  }
  sync() { this.sliders.forEach(function(input) { var val = this.state.get(input.id); if (val !== undefined) input.value = val; }, this); }
  syncLabels() {
    var all = this.state.getAll();
    this.sliders.forEach(function(input) {
      var val = all[input.id]; if (val !== undefined) {
        var badge = document.getElementById('badge-' + input.id);
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

    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Applied Force (F) <span class="ctrl-unit">N</span></span>
        <span class="val-badge" id="badge-applied_force">20</span>
      </div>
      <input type="range" id="applied_force" min="-40" max="80" step="1" value="20" aria-label="Applied force">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Mass (m) <span class="ctrl-unit">kg</span></span>
        <span class="val-badge" id="badge-mass">5</span>
      </div>
      <input type="range" id="mass" min="1" max="20" step="0.5" value="5" aria-label="Mass">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Friction (&mu;) <span class="ctrl-unit"></span></span>
        <span class="val-badge" id="badge-friction">0.20</span>
      </div>
      <input type="range" id="friction" min="0" max="1" step="0.02" value="0.2" aria-label="Friction coefficient">
    </div>"""

    values = """    <div class="vcard"><div class="lbl">Net Force</div><div class="num" id="val-net_force" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Acceleration</div><div class="num" id="val-acceleration" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">Velocity</div><div class="num" id="val-velocity" style="color:#06b6d4">0</div></div>
    <div class="vcard"><div class="lbl">Friction</div><div class="num" id="val-friction_force" style="color:#ef4444">0</div></div>"""

    return build_simulation_html(spec, custom_script=script, custom_controls=controls, custom_live_values=values, custom_assessment=_build_assessment(spec))


def _build_energy(spec: SimulationSpecification) -> str:
    script = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.time = 0; this.angle = Math.PI / 4;
  }
  update(dt, state) {
    this.time += dt;
    var mass = state.get('mass') || 1;
    var length = state.get('length') || 3;
    var g = 9.81;
    this.angle += (-g / length) * Math.sin(this.angle) * dt;
    var h = length * (1 - Math.cos(this.angle));
    var pe = mass * g * h;
    var total = mass * g * length * (1 - Math.cos(Math.PI / 4));
    var ke = Math.max(0, total - pe);
    state.set('potential_energy', parseFloat(pe.toFixed(2)));
    state.set('kinetic_energy', parseFloat(ke.toFixed(2)));
    state.set('total_energy', parseFloat(total.toFixed(2)));
    state.set('pendulum_angle', this.angle);
    state.set('height', parseFloat(h.toFixed(2)));
  }
  onReset() { this.time = 0; this.angle = Math.PI / 4; }
  getHint() { return 'Adjust mass & length to see energy changes'; }
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

    var cx = w / 2, cy = 60;
    var pivotLen = 120;
    var angle = state.get('pendulum_angle') || 0;
    var bobX = cx + pivotLen * Math.sin(angle);
    var bobY = cy + pivotLen * Math.cos(angle);
    var mass = Math.min(30, 10 + (state.get('mass') || 1) * 3);

    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(0, cy - 2, w, 4);
    ctx.fillStyle = '#94a3b8';
    ctx.beginPath(); ctx.arc(cx, cy, 6, 0, Math.PI * 2); ctx.fill();

    ctx.strokeStyle = '#64748b'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(bobX, bobY); ctx.stroke();

    ctx.shadowBlur = 15; ctx.shadowColor = 'rgba(99,102,241,0.3)';
    var grad = ctx.createRadialGradient(bobX - 5, bobY - 5, 3, bobX, bobY, mass);
    grad.addColorStop(0, '#a78bfa'); grad.addColorStop(1, '#6366f1');
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.arc(bobX, bobY, mass, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;

    var barX = 20, barY = 140, barW = w - 40, barH = 24;
    var pe = state.get('potential_energy') || 0;
    var ke = state.get('kinetic_energy') || 0;
    var total = state.get('total_energy') || 1;

    ctx.fillStyle = '#f1f5f9';
    ctx.beginPath(); ctx.roundRect(barX, barY, barW, barH, 6); ctx.fill();
    ctx.fillStyle = '#e2e8f0';
    ctx.beginPath(); ctx.roundRect(barX, barY + barH + 8, barW, barH, 6); ctx.fill();

    if (total > 0) {
      var peFrac = Math.max(0, Math.min(1, pe / total));
      var keFrac = Math.max(0, Math.min(1, ke / total));
      var barW1 = barW * peFrac;
      var barW2 = barW * keFrac;

      ctx.fillStyle = '#10b981';
      ctx.beginPath(); ctx.roundRect(barX, barY, Math.max(barW1, 2), barH, 6); ctx.fill();

      ctx.fillStyle = '#6366f1';
      ctx.beginPath(); ctx.roundRect(barX, barY + barH + 8, Math.max(barW2, 2), barH, 6); ctx.fill();
    }

    ctx.fillStyle = '#1e293b'; ctx.font = '10px sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('PE: ' + pe.toFixed(1) + ' J', barX + 8, barY + 16);
    ctx.fillText('KE: ' + ke.toFixed(1) + ' J', barX + 8, barY + barH + 24);
    ctx.fillStyle = '#64748b'; ctx.font = '9px sans-serif';
    ctx.fillText('Total: ' + total.toFixed(1) + ' J', barX + barW - 100, barY + 16);
  }
}

class ControlsManager {
  constructor(state, bus) { this.state = state; this.bus = bus; this.sliders = []; }
  bind() {
    var self = this;
    document.querySelectorAll('input[type="range"]').forEach(function(input) {
      if (input.id === 'speed-slider') return;
      var key = input.id; self.sliders.push(input);
      self.state.set(key, parseFloat(input.value));
      input.addEventListener('input', function() {
        var val = parseFloat(this.value);
        self.state.set(key, val);
        var badge = document.getElementById('badge-' + key);
        if (badge) badge.textContent = val.toFixed(1);
      });
    });
  }
  sync() { this.sliders.forEach(function(input) { var val = this.state.get(input.id); if (val !== undefined) input.value = val; }, this); }
  syncLabels() {
    var all = this.state.getAll();
    this.sliders.forEach(function(input) {
      var val = all[input.id]; if (val !== undefined) {
        var badge = document.getElementById('badge-' + input.id);
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

    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Mass (m) <span class="ctrl-unit">kg</span></span>
        <span class="val-badge" id="badge-mass">1.0</span>
      </div>
      <input type="range" id="mass" min="0.1" max="5" step="0.1" value="1" aria-label="Pendulum mass">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Pendulum Length (L) <span class="ctrl-unit">m</span></span>
        <span class="val-badge" id="badge-length">3.0</span>
      </div>
      <input type="range" id="length" min="0.5" max="5" step="0.1" value="3" aria-label="Pendulum length">
    </div>"""

    values = """    <div class="vcard"><div class="lbl">PE</div><div class="num" id="val-potential_energy" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">KE</div><div class="num" id="val-kinetic_energy" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Total E</div><div class="num" id="val-total_energy" style="color:#f59e0b">0</div></div>
    <div class="vcard"><div class="lbl">Height</div><div class="num" id="val-height" style="color:#06b6d4">0</div></div>"""

    return build_simulation_html(spec, custom_script=script, custom_controls=controls, custom_live_values=values, custom_assessment=_build_assessment(spec))


def _build_buoyancy(spec: SimulationSpecification) -> str:
    script = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.time = 0; this.blockY = 0; this.blockVy = 0; this.settled = false;
  }
  update(dt, state) {
    this.time += dt;
    var mass = state.get('mass') || 1;
    var volume = state.get('volume') || 0.001;
    var fluidDensity = state.get('fluid_density') || 1000;
    var g = state.get('gravity') || 9.81;
    var objDensity = mass / volume;
    var weight = mass * g;
    var densityRatio = objDensity / fluidDensity;
    var submergedFrac, buoyantForce;
    if (densityRatio >= 1) {
      submergedFrac = 1;
      buoyantForce = fluidDensity * volume * g;
    } else {
      submergedFrac = densityRatio;
      buoyantForce = weight;
    }
    var netForce = buoyantForce - weight;
    var maxDepth = 0.7;
    if (Math.abs(netForce) < 0.01) {
      this.blockVy *= 0.95;
      this.settled = true;
    } else {
      this.settled = false;
      var accel = netForce / mass;
      this.blockVy += accel * dt * 0.3;
      this.blockY += this.blockVy * dt;
    }
    if (this.blockY < -maxDepth * 0.5) { this.blockY = -maxDepth * 0.5; this.blockVy = 0; }
    if (this.blockY > maxDepth * 0.8) { this.blockY = maxDepth * 0.8; this.blockVy = 0; }
    state.set('weight', parseFloat(weight.toFixed(2)));
    state.set('buoyant_force', parseFloat(buoyantForce.toFixed(2)));
    state.set('net_force', parseFloat(netForce.toFixed(2)));
    state.set('submerged_fraction', parseFloat(Math.min(1, submergedFrac + Math.max(0, this.blockY / maxDepth) * 0.2).toFixed(3)));
    state.set('density_ratio', parseFloat(densityRatio.toFixed(3)));
    state.set('object_density', parseFloat(objDensity.toFixed(1)));
    state.set('fluid_density_val', fluidDensity);
    state.set('block_depth', this.blockY);
    state.set('settled', this.settled);
  }
  onReset() { this.time = 0; this.blockY = 0; this.blockVy = 0; this.settled = false; }
  canvasInteractions(canvas, state, bus) {
    var self = this;
    canvas.addEventListener('click', function(e) {
      var rect = canvas.getBoundingClientRect();
      var scaleX = canvas.width / rect.width;
      var cx = (e.clientX - rect.left) * scaleX;
      var w = canvas.width, h = canvas.height;
      var tankLeft = w * 0.15, tankRight = w * 0.85;
      var tankTop = h * 0.15, tankBottom = h * 0.85;
      if (cx > tankLeft && cx < tankRight) {
        var depth = (cx - tankLeft) / (tankRight - tankLeft);
        state.set('volume', parseFloat((0.0005 + depth * 0.002).toFixed(4)));
        document.getElementById('badge-volume').textContent = (0.0005 + depth * 0.002).toFixed(4);
        document.getElementById('volume').value = (0.0005 + depth * 0.002);
        self.blockVy = 0;
      }
    });
  }
  getHint() {
    var settled = this.state.get('settled');
    if (settled) return 'Block at equilibrium - adjust mass, volume, or fluid density';
    return 'Block in motion - observe buoyant force vs weight';
  }
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

    var tankLeft = w * 0.15, tankRight = w * 0.85;
    var tankTop = h * 0.15, tankBottom = h * 0.85;
    var tankW = tankRight - tankLeft, tankH = tankBottom - tankTop;
    var waterLevel = tankTop + tankH * 0.75;

    ctx.fillStyle = '#e0f2fe'; ctx.fillRect(tankLeft, waterLevel, tankW, tankBottom - waterLevel);
    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 2;
    ctx.strokeRect(tankLeft, tankTop, tankW, tankH);
    ctx.strokeStyle = '#bae6fd'; ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 3]);
    ctx.beginPath(); ctx.moveTo(tankLeft, waterLevel); ctx.lineTo(tankRight, waterLevel); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#0ea5e9'; ctx.font = '9px sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('Water Level', tankLeft + 6, waterLevel - 4);

    var vol = state.get('volume') || 0.001;
    var blockArea = Math.min(tankW * 0.3, Math.max(tankW * 0.1, vol * 15000));
    var blockSize = Math.sqrt(blockArea);
    var depth = state.get('block_depth') || 0;
    var densityRatio = state.get('density_ratio') || 1;
    var bx = (tankLeft + tankRight) / 2;
    var by = waterLevel + (tankBottom - waterLevel) * (0.5 + depth * 0.5) - blockSize / 2;
    by = Math.max(waterLevel - blockSize * 0.8, Math.min(tankBottom - blockSize, by));

    var submergedFrac = state.get('submerged_fraction') || 0;
    var submergedH = blockSize * Math.min(1, Math.max(0, submergedFrac));
    var aboveH = blockSize - submergedH;

    var aboveY = by - aboveH;
    var subY = by;

    if (aboveH > 0 && densityRatio < 1) {
      ctx.fillStyle = '#e2e8f0';
      ctx.fillRect(bx - blockSize / 2, aboveY, blockSize, aboveH);
      ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1;
      ctx.strokeRect(bx - blockSize / 2, aboveY, blockSize, aboveH);
    }

    if (submergedH > 0) {
      var subGrad = ctx.createLinearGradient(0, subY, 0, subY + submergedH);
      var baseR = densityRatio < 1 ? '34,197,94' : densityRatio > 1.5 ? '239,68,68' : '234,179,8';
      subGrad.addColorStop(0, 'rgba(' + baseR + ',0.6)');
      subGrad.addColorStop(1, 'rgba(' + baseR + ',0.9)');
      ctx.fillStyle = subGrad;
      ctx.fillRect(bx - blockSize / 2, subY, blockSize, submergedH);
      ctx.strokeStyle = baseR === '34,197,94' ? '#16a34a' : baseR === '239,68,68' ? '#dc2626' : '#ca8a04';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(bx - blockSize / 2, subY, blockSize, submergedH);
    }

    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText((state.get('mass') || 1) + 'kg', bx, by + blockSize / 2 + 4);

    var weight = state.get('weight') || 9.81;
    var buoyant = state.get('buoyant_force') || 0;
    var net = state.get('net_force') || 0;
    var arrowScale = 0.02;
    var arrowLen = Math.min(80, Math.max(15, weight * arrowScale));
    var arrowLenB = Math.min(80, Math.max(15, buoyant * arrowScale));

    ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(bx, by + blockSize / 2 + 8);
    ctx.lineTo(bx, by + blockSize / 2 + 8 + arrowLen);
    ctx.stroke();
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.moveTo(bx - 4, by + blockSize / 2 + 8 + arrowLen - 8);
    ctx.lineTo(bx, by + blockSize / 2 + 8 + arrowLen);
    ctx.lineTo(bx + 4, by + blockSize / 2 + 8 + arrowLen - 8);
    ctx.fill();
    ctx.fillStyle = '#ef4444'; ctx.font = '9px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('W=' + weight.toFixed(1) + 'N', bx, by + blockSize / 2 + 8 + arrowLen + 14);

    ctx.strokeStyle = '#0ea5e9'; ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(bx, by - 8);
    ctx.lineTo(bx, by - 8 - arrowLenB);
    ctx.stroke();
    ctx.fillStyle = '#0ea5e9';
    ctx.beginPath();
    ctx.moveTo(bx - 4, by - 8 - arrowLenB + 8);
    ctx.lineTo(bx, by - 8 - arrowLenB);
    ctx.lineTo(bx + 4, by - 8 - arrowLenB + 8);
    ctx.fill();
    ctx.fillStyle = '#0ea5e9'; ctx.font = '9px sans-serif';
    ctx.fillText('F_b=' + buoyant.toFixed(1) + 'N', bx, by - 8 - arrowLenB - 6);

    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('Net: ' + net.toFixed(1) + ' N', 10, 18);
    ctx.fillStyle = '#475569'; ctx.font = '11px "Courier New", monospace';
    ctx.fillText('\\u03c1_obj = ' + (state.get('object_density') || 0).toFixed(0) + ' kg/m' + String.fromCharCode(179), 10, 36);
    ctx.fillStyle = '#6366f1';
    ctx.fillText('\\u03c1_ratio = ' + (state.get('density_ratio') || 0).toFixed(2), 10, 54);

    var settled = state.get('settled');
    var hintY = h - 12;
    ctx.fillStyle = '#94a3b8'; ctx.font = '9px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText(settled ? 'Click tank to adjust volume' : 'Block in motion...', w - 10, hintY);
  }
}

class ControlsManager {
  constructor(state, bus) { this.state = state; this.bus = bus; this.sliders = []; }
  bind() {
    var self = this;
    document.querySelectorAll('input[type="range"]').forEach(function(input) {
      if (input.id === 'speed-slider') return;
      var key = input.id; self.sliders.push(input);
      self.state.set(key, parseFloat(input.value));
      input.addEventListener('input', function() {
        var val = parseFloat(this.value);
        self.state.set(key, val);
        var badge = document.getElementById('badge-' + key);
        if (badge) badge.textContent = key === 'volume' ? val.toFixed(4) : val.toFixed(1);
      });
    });
  }
  sync() { this.sliders.forEach(function(input) { var val = this.state.get(input.id); if (val !== undefined) input.value = val; }, this); }
  syncLabels() {
    var all = this.state.getAll();
    this.sliders.forEach(function(input) {
      var val = all[input.id]; if (val !== undefined) {
        var badge = document.getElementById('badge-' + input.id);
        if (badge) badge.textContent = input.id === 'volume' ? parseFloat(val).toFixed(4) : parseFloat(val).toFixed(1);
      }
    });
  }
}
class AssessmentEngine {
  constructor(state, bus) { this.state = state; this.bus = bus; }
  getCurrentQuestion() { return document.getElementById('assess-q')?.textContent || ''; }
}
"""

    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Mass (m) <span class="ctrl-unit">kg</span></span>
        <span class="val-badge" id="badge-mass">1.0</span>
      </div>
      <input type="range" id="mass" min="0.1" max="5" step="0.1" value="1" aria-label="Object mass">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Volume (V) <span class="ctrl-unit">m&sup3;</span></span>
        <span class="val-badge" id="badge-volume">0.0010</span>
      </div>
      <input type="range" id="volume" min="0.0003" max="0.003" step="0.0001" value="0.001" aria-label="Object volume">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Fluid Density (&rho;<sub>f</sub>) <span class="ctrl-unit">kg/m&sup3;</span></span>
        <span class="val-badge" id="badge-fluid_density">1000</span>
      </div>
      <input type="range" id="fluid_density" min="100" max="2000" step="10" value="1000" aria-label="Fluid density">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Gravity (g) <span class="ctrl-unit">m/s&sup2;</span></span>
        <span class="val-badge" id="badge-gravity">9.81</span>
      </div>
      <input type="range" id="gravity" min="0.1" max="30" step="0.1" value="9.81" aria-label="Gravity">
    </div>"""

    presets = """  <div class="presets">
    <span style="font-size:9px;color:#64748b;font-weight:600;padding-right:4px">Presets:</span>
    <button data-mass="0.5" data-volume="0.002" data-density="1000" data-gravity="9.81">Floats (Cork)</button>
    <button data-mass="1" data-volume="0.001" data-density="1260" data-gravity="9.81">Neutral (Fish)</button>
    <button data-mass="3" data-volume="0.0005" data-density="1000" data-gravity="9.81">Sinks (Rock)</button>
    <button data-mass="1" data-volume="0.001" data-density="1000" data-gravity="1.62">Moon</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var mass = this.getAttribute('data-mass');
        var volume = this.getAttribute('data-volume');
        var density = this.getAttribute('data-density');
        var gravity = this.getAttribute('data-gravity');
        document.getElementById('mass').value = mass;
        document.getElementById('volume').value = volume;
        document.getElementById('fluid_density').value = density;
        document.getElementById('gravity').value = gravity;
        document.getElementById('badge-mass').textContent = mass;
        document.getElementById('badge-volume').textContent = volume;
        document.getElementById('badge-fluid_density').textContent = density;
        document.getElementById('badge-gravity').textContent = gravity;
        state.set('mass', parseFloat(mass));
        state.set('volume', parseFloat(volume));
        state.set('fluid_density', parseFloat(density));
        state.set('gravity', parseFloat(gravity));
        var engine = window._engine;
        if (engine) { engine.blockVy = 0; engine.blockY = 0; engine.settled = false; }
      });
    });
"""

    script = script.replace(
        "class ControlsManager {",
        presets_script + "\n\nclass ControlsManager {"
    )

    values = """    <div class="vcard"><div class="lbl">Weight</div><div class="num" id="val-weight" style="color:#ef4444">0</div></div>
    <div class="vcard"><div class="lbl">Buoyant Force</div><div class="num" id="val-buoyant_force" style="color:#0ea5e9">0</div></div>
    <div class="vcard"><div class="lbl">Net Force</div><div class="num" id="val-net_force" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">&rho; ratio</div><div class="num" id="val-density_ratio" style="color:#f59e0b">0</div></div>
    <div class="vcard"><div class="lbl">Submerged</div><div class="num" id="val-submerged_fraction" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">Obj &rho;</div><div class="num" id="val-object_density" style="color:#06b6d4">0</div></div>"""

    graph = """  <div class="graph-area">
    <div class="graph-header">
      <div class="gt">Buoyancy Forces</div>
      <div class="gl"><span><span class="dot" style="background:#ef4444"></span>Weight</span><span><span class="dot" style="background:#0ea5e9"></span>Buoyant</span></div>
    </div>
    <canvas id="graph-canvas" width="700" height="180" aria-label="Buoyancy force graph"></canvas>
  </div>"""

    graph_data_push = """
if (typeof graphMgr !== 'undefined' && graphMgr) {
  graphMgr.setRange(0, 10, 0, 50);
  graphMgr.pushData('Weight', parseFloat(state.get('weight') || 0));
  graphMgr.pushData('Buoyant', parseFloat(state.get('buoyant_force') || 0));
}
"""

    script = script.replace(
        "__GRAPH_DATA_PUSH_PLACEHOLDER__",
        graph_data_push
    )

    return build_simulation_html(
        spec,
        custom_script=script,
        custom_controls=controls,
        custom_live_values=values,
        custom_graph=graph,
        custom_assessment=_build_assessment(spec),
        custom_presets=presets,
    )


def _build_generic_physics(spec: SimulationSpecification) -> str:
    return """
class SimulationEngine {
  constructor(canvas, state, bus) { this.canvas = canvas; this.state = state; this.bus = bus; }
  update(dt, state) {}
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
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 16px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('Physics Simulation', w / 2, h / 2 - 10);
    ctx.fillStyle = '#64748b'; ctx.font = '13px sans-serif';
    ctx.fillText('Adjust controls and press Play', w / 2, h / 2 + 16);
    ctx.textAlign = 'left';
  }
}
class ControlsManager {
  constructor(state, bus) { this.state = state; this.bus = bus; this.sliders = []; }
  bind() {
    var self = this;
    document.querySelectorAll('input[type="range"]').forEach(function(input) {
      if (input.id === 'speed-slider') return;
      var key = input.id; self.sliders.push(input);
      self.state.set(key, parseFloat(input.value));
      input.addEventListener('input', function() {
        var val = parseFloat(this.value); self.state.set(key, val);
        var badge = document.getElementById('badge-' + key);
        if (badge) badge.textContent = val.toFixed(1);
      });
    });
  }
  sync() { this.sliders.forEach(function(input) { var val = this.state.get(input.id); if (val !== undefined) input.value = val; }, this); }
  syncLabels() {
    var all = this.state.getAll();
    this.sliders.forEach(function(input) {
      var val = all[input.id]; if (val !== undefined) {
        var badge = document.getElementById('badge-' + input.id);
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


def _build_assessment(spec: SimulationSpecification) -> str:
    ap = spec.assessment_prompts[0] if spec.assessment_prompts else None
    if not ap:
        return ""
    return f"""  <div class="assess-area" id="assess-area">
    <div class="ql">{"Try This"}</div>
    <div class="q" id="assess-q">{ap.question}</div>
    <div class="h" id="assess-h">{ap.hint}</div>
  </div>"""
