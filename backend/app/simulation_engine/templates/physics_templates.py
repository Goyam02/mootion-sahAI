from __future__ import annotations

from app.simulation_engine.schemas import SimulationSpecification, SimulationType
from app.simulation_engine.templates.base_template import (
    build_simulation_html,
    build_custom_llm_simulation,
    _build_assessment_html,
)


# ────────────────────────────────────────────────────────────────────────────
# NOTE: ControlsManager and AssessmentEngine are NOT defined here.
# base_template._build_script() automatically appends SHARED_CONTROLS_MANAGER.
# Only SimulationEngine + Renderer need to be provided per simulation.
# ────────────────────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════
#  PROJECTILE MOTION
# ══════════════════════════════════════════════════════════════════════════

PROJECTILE_MOTION_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.trail   = [];
    this.maxTrail = 600;
    this.time    = 0;
    this.px = 70; this.py = 0;
    this.vx = 0;  this.vy = 0;
    this.launched = false;
    this.readyToLaunch = true;
    this._minPy = undefined;
    this.groundY = 0;
  }

  update(dt, state) {
    const g      = state.get('gravity') || 9.81;
    const angle  = state.get('angle')   || 45;
    const speed  = state.get('initial_velocity') || 20;
    const h      = this.canvas.height;
    this.groundY = h - 40;

    if (!this.launched && this.readyToLaunch) {
      const rad  = angle * Math.PI / 180;
      // pixel scale: 1 m = 8 px
      this.vx = speed * Math.cos(rad) * 8;
      this.vy = -speed * Math.sin(rad) * 8;
      this.px = 70; this.py = this.groundY;
      this.trail = []; this.time = 0;
      this._minPy = this.groundY;
      this.launched = true; this.readyToLaunch = false;
      state.set('in_flight', true);
      state.set('max_height', 0);
      state.set('range', 0);
    }

    if (this.launched) {
      this.time += dt;
      this.px += this.vx * dt;
      this.vy += g * 8 * dt;   // g in px/s² (8 px per metre)
      this.py += this.vy * dt;

      if (this.py >= this.groundY) {
        this.py = this.groundY; this.vy = 0; this.vx = 0;
        this.launched = false;
        state.set('in_flight', false);
      }

      if (this.py < this._minPy) {
        this._minPy = this.py;
        state.set('max_height', parseFloat(((this.groundY - this._minPy) / 8).toFixed(2)));
      }

      const spd = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
      state.set('pos_x',          parseFloat(((this.px - 70) / 8).toFixed(2)));
      state.set('pos_y',          parseFloat(((this.groundY - this.py) / 8).toFixed(2)));
      state.set('vel_x',          parseFloat((this.vx / 8).toFixed(2)));
      state.set('vel_y',          parseFloat((-this.vy / 8).toFixed(2)));
      state.set('time_of_flight', parseFloat(this.time.toFixed(2)));
      state.set('speed',          parseFloat((spd / 8).toFixed(2)));
      state.set('range',          parseFloat(((this.px - 70) / 8).toFixed(2)));

      this.trail.push({ x: this.px, y: this.py });
      if (this.trail.length > this.maxTrail) this.trail.shift();
    }
  }

  onReset() {
    this.trail = []; this.launched = false; this.readyToLaunch = true;
    this.time = 0; this._minPy = undefined;
    this.px = 70; this.py = 0;
  }

  canvasInteractions(canvas, state, bus) {
    const self = this;
    function setAngleFromClick(clientX, clientY) {
      const rect   = canvas.getBoundingClientRect();
      const scaleX = canvas.width  / rect.width;
      const scaleY = canvas.height / rect.height;
      const cx     = (clientX - rect.left)  * scaleX;
      const cy     = (clientY - rect.top)   * scaleY;
      const angle  = Math.atan2(-(cy - self.groundY), cx - 70) * 180 / Math.PI;
      if (angle > 2 && angle < 88) {
        const rounded = Math.round(angle);
        state.set('angle', rounded);
        const el = document.getElementById('angle');
        if (el) el.value = rounded;
        const badge = document.getElementById('badge-angle');
        if (badge) badge.textContent = rounded;
        if (!self.launched) { self.readyToLaunch = true; self.trail = []; self._minPy = undefined; }
      }
    }
    canvas.addEventListener('click', function(e) { setAngleFromClick(e.clientX, e.clientY); });
    canvas.addEventListener('touchend', function(e) {
      e.preventDefault();
      setAngleFromClick(e.changedTouches[0].clientX, e.changedTouches[0].clientY);
    });
  }

  getHint() {
    if (!this.launched && this.trail.length === 0) return 'Click canvas to set launch angle, then press ▶ Play';
    if (this.launched)  return 'In flight — watch velocity vectors';
    return 'Landed! Adjust parameters and reset to try again.';
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

    // Sky gradient
    const sky = ctx.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, '#e0f2fe'); sky.addColorStop(1, '#f8fafc');
    ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);

    const groundY = h - 40;

    // Grid
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, groundY); ctx.stroke(); }
    for (let y = 0; y < groundY; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    // Ground
    ctx.fillStyle = '#d1fae5'; ctx.fillRect(0, groundY, w, h - groundY);
    ctx.fillStyle = '#6ee7b7'; ctx.fillRect(0, groundY, w, 4);
    ctx.fillStyle = '#374151'; ctx.font = '8px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('0 m', 68, groundY - 4);

    // Distance ticks
    ctx.fillStyle = '#94a3b8'; ctx.font = '8px "Courier New", monospace'; ctx.textAlign = 'center';
    for (let m = 10; m <= 120; m += 10) {
      const px = 70 + m * 8;
      if (px > w - 5) break;
      ctx.beginPath(); ctx.moveTo(px, groundY); ctx.lineTo(px, groundY + 6); ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1; ctx.stroke();
      ctx.fillText(m + 'm', px, groundY + 16);
    }

    const engine = window._engine;

    // Trail
    if (engine && engine.trail.length > 1) {
      const grad = ctx.createLinearGradient(70, 0, engine.px, 0);
      grad.addColorStop(0, 'rgba(99,102,241,0.3)');
      grad.addColorStop(1, '#8b5cf6');
      ctx.strokeStyle = grad; ctx.lineWidth = 2.5; ctx.lineJoin = 'round';
      ctx.beginPath();
      engine.trail.forEach(function(p, i) { if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y); });
      ctx.stroke();
    }

    if (engine) {
      const px = engine.px, py = engine.py;
      const angle = state.get('angle') || 45;
      const speed = state.get('initial_velocity') || 20;

      // Projectile ball
      const ballGrad = ctx.createRadialGradient(px - 3, py - 3, 1, px, py, 12);
      ballGrad.addColorStop(0, '#c4b5fd'); ballGrad.addColorStop(1, '#7c3aed');
      ctx.shadowBlur = engine.launched ? 18 : 0; ctx.shadowColor = '#8b5cf6';
      ctx.fillStyle = ballGrad;
      ctx.beginPath(); ctx.arc(px, py, 11, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;

      // Launch arrow (pre-launch)
      if (!engine.launched && engine.trail.length === 0) {
        const rad      = angle * Math.PI / 180;
        const arrowLen = Math.min(70, speed * 3.5);
        const ax = px + arrowLen * Math.cos(rad);
        const ay = py - arrowLen * Math.sin(rad);
        ctx.strokeStyle = '#4f46e5'; ctx.lineWidth = 2.5; ctx.setLineDash([6, 4]);
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(ax, ay); ctx.stroke(); ctx.setLineDash([]);
        // arrowhead
        ctx.fillStyle = '#4f46e5';
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax - 9 * Math.cos(rad - 0.4), ay + 9 * Math.sin(rad - 0.4));
        ctx.lineTo(ax - 9 * Math.cos(rad + 0.4), ay + 9 * Math.sin(rad + 0.4));
        ctx.closePath(); ctx.fill();
        // labels
        ctx.font = 'bold 11px sans-serif'; ctx.fillStyle = '#1e293b'; ctx.textAlign = 'center';
        ctx.fillText(speed + ' m/s', ax + 10, ay - 10);
        ctx.fillStyle = '#d97706'; ctx.font = '11px sans-serif';
        ctx.fillText(angle + '°', px + 28, py - 8);
        ctx.textAlign = 'left';
      }

      // Velocity vectors (in-flight)
      if (engine.launched) {
        const vx = state.get('vel_x') || 0;
        const vy = -state.get('vel_y') || 0;  // vy is positive-up in state
        const sc = 3;
        // Vx
        ctx.strokeStyle = '#10b981'; ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px + vx * sc, py); ctx.stroke();
        ctx.fillStyle = '#10b981'; ctx.font = '9px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText('vx', px + vx * sc * 0.5, py - 5);
        // Vy
        ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px, py + vy * sc); ctx.stroke();
        ctx.fillStyle = '#f59e0b';
        ctx.fillText('vy', px + 12, py + vy * sc * 0.5);
        ctx.textAlign = 'left';
      }
    }

    // HUD
    ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.beginPath(); ctx.roundRect(8, 8, 200, 72, 8); ctx.fill();
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('Time:  ' + (state.get('time_of_flight') || 0).toFixed(2) + ' s',  16, 26);
    ctx.fillText('Range: ' + (state.get('range')          || 0).toFixed(2) + ' m',  16, 44);
    ctx.fillText('H_max: ' + (state.get('max_height')     || 0).toFixed(2) + ' m',  16, 62);
    ctx.fillStyle = '#475569'; ctx.font = '9px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('Click to aim', w - 10, h - 10);
  }
}
"""


# ══════════════════════════════════════════════════════════════════════════
#  ELECTRICITY (Ohm's Law)
# ══════════════════════════════════════════════════════════════════════════

ELECTRICITY_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.particles = [];
    for (let i = 0; i < 35; i++) {
      this.particles.push({
        x: Math.random(),
        y: 0.18 + Math.random() * 0.64,
        phase: Math.random() * Math.PI * 2,
      });
    }
    this.time = 0;
  }

  update(dt, state) {
    this.time += dt;
    const V = state.get('voltage')    || 5;
    const R = state.get('resistance') || 10;
    const I = V / R;
    state.set('current', parseFloat(I.toFixed(3)));
    state.set('power',   parseFloat((V * I).toFixed(3)));
    state.set('voltage', V);
    state.set('resistance', R);

    const speed = Math.min(0.6, I * 0.4);
    for (let i = 0; i < this.particles.length; i++) {
      this.particles[i].x += speed * dt;
      if (this.particles[i].x > 1) this.particles[i].x -= 1;
    }
  }

  onReset() { this.time = 0; }

  canvasInteractions(canvas, state, bus) {
    let dragging = false;
    function fromY(clientY) {
      const rect  = canvas.getBoundingClientRect();
      const scaleY = canvas.height / rect.height;
      const cy    = (clientY - rect.top) * scaleY;
      const r     = 5 + (cy / canvas.height) * 95;
      return parseFloat(Math.min(100, Math.max(5, r)).toFixed(1));
    }
    canvas.addEventListener('mousedown',  function(e) { dragging = true;  state.set('resistance', fromY(e.clientY)); });
    canvas.addEventListener('mousemove',  function(e) { if (dragging) state.set('resistance', fromY(e.clientY)); });
    canvas.addEventListener('mouseup',    function()  { dragging = false; });
    canvas.addEventListener('mouseleave', function()  { dragging = false; });
    canvas.addEventListener('touchstart', function(e) { e.preventDefault(); state.set('resistance', fromY(e.touches[0].clientY)); }, { passive: false });
    canvas.addEventListener('touchmove',  function(e) { e.preventDefault(); state.set('resistance', fromY(e.touches[0].clientY)); }, { passive: false });
  }

  getHint() { return 'Drag up/down on the resistor to change its value'; }
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

    const V  = state.get('voltage')    || 5;
    const R  = state.get('resistance') || 10;
    const I  = V / R;
    const P  = V * I;

    // Wire top / bottom
    const wireY1 = h * 0.35, wireY2 = h * 0.65;
    const wireX1 = 60, wireX2 = w - 60;

    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 4; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(wireX1, wireY1); ctx.lineTo(wireX2, wireY1); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(wireX1, wireY2); ctx.lineTo(wireX2, wireY2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(wireX2, wireY1); ctx.lineTo(wireX2, wireY2); ctx.stroke();

    // Battery (left side)
    const batW = 36, batH = 70;
    const batX = wireX1 - batW / 2, batY = (wireY1 + wireY2) / 2 - batH / 2;
    ctx.beginPath(); ctx.moveTo(wireX1, wireY1); ctx.lineTo(wireX1, batY); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(wireX1, batY + batH); ctx.lineTo(wireX1, wireY2); ctx.stroke();

    const batGrad = ctx.createLinearGradient(batX, 0, batX + batW, 0);
    batGrad.addColorStop(0, '#059669'); batGrad.addColorStop(1, '#10b981');
    ctx.fillStyle = batGrad;
    ctx.beginPath(); ctx.roundRect(batX, batY, batW, batH, 6); ctx.fill();
    // +/- terminals
    ctx.fillStyle = '#fff'; ctx.font = 'bold 16px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('+', wireX1, batY + 22);
    ctx.fillText('−', wireX1, batY + batH - 8);
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText(V.toFixed(1) + 'V', wireX1, batY + batH / 2 + 4);

    // Resistor (right side, zig-zag)
    const resH  = Math.min(90, Math.max(28, R * 0.9));
    const resX  = wireX2;
    const resY  = (wireY1 + wireY2) / 2 - resH / 2;
    const rHeat = Math.min(1, I / 2.4); // heat intensity 0→1

    ctx.beginPath(); ctx.moveTo(resX, wireY1); ctx.lineTo(resX, resY); ctx.stroke();

    // zigzag body
    const steps = 8;
    const stepH = resH / steps;
    const zigW  = 18;
    ctx.strokeStyle = `rgb(${Math.round(100 + 155 * rHeat)},${Math.round(100 - 60 * rHeat)},${Math.round(100 - 80 * rHeat)})`;
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(resX, resY);
    for (let i = 0; i < steps; i++) {
      const xt = resX + (i % 2 === 0 ? zigW : -zigW);
      const yt = resY + stepH * (i + 0.5);
      ctx.lineTo(xt, yt);
    }
    ctx.lineTo(resX, resY + resH); ctx.stroke();

    // Resistor label
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(R.toFixed(0) + ' Ω', resX + 30, resY + resH / 2 + 4);

    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(resX, resY + resH); ctx.lineTo(resX, wireY2); ctx.stroke();

    // Electrons
    const engine = window._engine;
    if (engine) {
      const pathLen = (wireX2 - wireX1) + (wireY2 - wireY1); // approx loop length
      engine.particles.forEach(function(p) {
        // map particle x (0→1) to circuit path
        const frac = p.x;
        let ex, ey;
        const topFrac  = (wireX2 - wireX1) / (2 * pathLen);
        const sideFrac = (wireY2 - wireY1) / (2 * pathLen);
        const batFrac  = sideFrac;
        if (frac < topFrac) {
          // top wire left→right
          ex = wireX1 + frac / topFrac * (wireX2 - wireX1 - 60);
          ey = wireY1;
        } else if (frac < topFrac + sideFrac) {
          // right side going down
          ex = wireX2;
          ey = wireY1 + (frac - topFrac) / sideFrac * (wireY2 - wireY1);
        } else {
          // bottom wire right→left
          ex = wireX2 - (frac - topFrac - sideFrac) / topFrac * (wireX2 - wireX1 - 60);
          ey = wireY2;
        }
        const bright = 0.5 + 0.5 * Math.sin(p.phase + performance.now() * 0.002);
        ctx.fillStyle = `rgba(99, 102, 241, ${0.55 + bright * 0.45})`;
        ctx.shadowBlur = 6; ctx.shadowColor = '#6366f1';
        ctx.beginPath(); ctx.arc(ex, ey, 4, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0;
      });
    }

    // HUD
    ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.beginPath(); ctx.roundRect(8, 8, 195, 80, 8); ctx.fill();
    ctx.textAlign = 'left'; ctx.fillStyle = '#1e293b'; ctx.font = 'bold 12px "Courier New", monospace';
    ctx.fillText('I = ' + I.toFixed(3) + ' A',         16, 28);
    ctx.fillText('V = ' + V.toFixed(1) + ' V',         16, 48);
    ctx.fillText('P = ' + P.toFixed(2) + ' W',         16, 68);
    ctx.fillStyle = '#475569'; ctx.font = '9px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('V = IR   P = IV', w - 10, h - 10);
  }
}
"""


# ══════════════════════════════════════════════════════════════════════════
#  WAVES
# ══════════════════════════════════════════════════════════════════════════

WAVES_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.time = 0;
  }

  update(dt, state) {
    this.time += dt;
    const freq  = state.get('frequency')  || 2;
    const amp   = state.get('amplitude')  || 50;
    const spd   = state.get('speed')      || 60;
    const sup   = state.get('superposition') || 0;
    const w     = this.canvas.width;

    const k  = freq * 0.02;
    const wv = spd  * 0.03;

    const pts1 = [], pts2 = [], ptsR = [];
    for (let x = 0; x <= w; x += 2) {
      const y1 = amp * Math.sin(k * x - wv * this.time);
      const y2 = amp * 0.65 * Math.sin(k * x * 0.75 - wv * 1.3 * this.time + sup * 2.2);
      pts1.push({ x, y: y1 });
      pts2.push({ x, y: y2 });
      ptsR.push({ x, y: y1 + y2 });
    }

    state.set('wave1',       pts1);
    state.set('wave2',       pts2);
    state.set('wave_result', ptsR);

    // derived quantities
    const wavelength = spd / freq;
    const period     = 1 / freq;
    state.set('wavelength', parseFloat(wavelength.toFixed(2)));
    state.set('period',     parseFloat(period.toFixed(2)));
  }

  onReset() { this.time = 0; }
  getHint()  { return 'Increase Superposition to see wave interference'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#f0f9ff'; ctx.fillRect(0, 0, w, h);

    // grid
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 50) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    const cy  = h / 2;
    const sup = state.get('superposition') || 0;

    // Axis
    ctx.strokeStyle = '#cbd5e1'; ctx.lineWidth = 1.5; ctx.setLineDash([6, 4]);
    ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(w, cy); ctx.stroke();
    ctx.setLineDash([]);

    function drawWave(points, color, lw, alpha) {
      if (!points || points.length < 2) return;
      ctx.save();
      ctx.globalAlpha = alpha || 1;
      ctx.strokeStyle = color; ctx.lineWidth = lw || 2; ctx.lineJoin = 'round';
      ctx.beginPath();
      points.forEach(function(p, i) {
        if (i === 0) ctx.moveTo(p.x, cy - p.y); else ctx.lineTo(p.x, cy - p.y);
      });
      ctx.stroke();
      ctx.restore();
    }

    if (sup > 0.05) drawWave(state.get('wave2'),       '#94a3b8', 1.5, 0.7);
    if (sup > 0.15) drawWave(state.get('wave_result'), '#ef4444', 3.0, 1.0);
    drawWave(state.get('wave1'), '#6366f1', 2.5, 1.0);

    // Legend
    const legends = [{ label: 'Wave 1', color: '#6366f1' }];
    if (sup > 0.05) legends.push({ label: 'Wave 2', color: '#94a3b8' });
    if (sup > 0.15) legends.push({ label: 'Resultant', color: '#ef4444' });
    let lx = w - 10;
    legends.forEach(function(l) {
      ctx.textAlign = 'right'; ctx.fillStyle = l.color; ctx.font = 'bold 10px sans-serif';
      ctx.fillText('■ ' + l.label, lx, 18);
      lx -= ctx.measureText('■ ' + l.label).width + 14;
    });

    // HUD
    const freq = state.get('frequency') || 2;
    const amp  = state.get('amplitude') || 50;
    const spd  = state.get('speed')     || 60;
    ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.beginPath(); ctx.roundRect(8, 8, 188, 72, 8); ctx.fill();
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('f  = ' + freq.toFixed(1) + ' Hz',                 16, 26);
    ctx.fillText('λ  = ' + (state.get('wavelength') || 0) + ' units', 16, 44);
    ctx.fillText('T  = ' + (state.get('period')     || 0) + ' s',    16, 62);
  }
}
"""


# ══════════════════════════════════════════════════════════════════════════
#  FORCES (Newton's 2nd Law)
# ══════════════════════════════════════════════════════════════════════════

FORCES_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.pos  = this.canvas.width / 2;
    this.vel  = 0;
    this.time = 0;
  }

  update(dt, state) {
    this.time += dt;
    const mass     = state.get('mass')          || 5;
    const applied  = state.get('applied_force') || 20;
    const mu       = state.get('friction')      || 0.2;
    const g        = 9.81;

    const normal   = mass * g;
    const fMax     = mu * normal;
    const fFric    = this.vel === 0 && Math.abs(applied) < fMax
                       ? 0
                       : (this.vel >= 0 ? -1 : 1) * Math.min(fMax, Math.abs(applied) * 0.8);
    const net      = applied + fFric;
    const accel    = net / mass;
    this.vel      += accel * dt * 60;   // scale for visibility
    this.vel      *= 0.995;             // slight damping
    this.pos      += this.vel * dt;

    // bounds
    const margin = 40;
    if (this.pos < margin)           { this.pos = margin;                 this.vel = 0; }
    if (this.pos > this.canvas.width - margin) { this.pos = this.canvas.width - margin; this.vel = 0; }

    state.set('net_force',     parseFloat(net.toFixed(2)));
    state.set('acceleration',  parseFloat(accel.toFixed(3)));
    state.set('velocity',      parseFloat((this.vel / 60).toFixed(3)));
    state.set('friction_force',parseFloat(fFric.toFixed(2)));
    state.set('normal_force',  parseFloat(normal.toFixed(1)));
    state.set('weight',        parseFloat((mass * g).toFixed(1)));
    state.set('block_x',       this.pos);
  }

  onReset() { this.pos = this.canvas.width / 2; this.vel = 0; this.time = 0; }

  canvasInteractions(canvas, state, bus) {
    canvas.addEventListener('click', function(e) {
      const rect  = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const cx    = (e.clientX - rect.left) * scaleX;
      const force = ((cx - canvas.width / 2) / (canvas.width / 2 - 40)) * 80;
      const clamped = parseFloat(Math.max(-40, Math.min(80, force)).toFixed(1));
      state.set('applied_force', clamped);
      const el = document.getElementById('applied_force');
      if (el) el.value = clamped;
      const badge = document.getElementById('badge-applied_force');
      if (badge) badge.textContent = clamped;
    });
  }

  getHint() { return 'Click on canvas to set the applied force direction & size'; }
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

    // Floor
    const floorY = h - 55;
    const floorGrad = ctx.createLinearGradient(0, floorY, 0, h);
    floorGrad.addColorStop(0, '#e2e8f0'); floorGrad.addColorStop(1, '#cbd5e1');
    ctx.fillStyle = floorGrad; ctx.fillRect(0, floorY, w, h - floorY);
    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(0, floorY); ctx.lineTo(w, floorY); ctx.stroke();
    // hatch marks on floor
    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1;
    for (let x = 10; x < w; x += 20) {
      ctx.beginPath(); ctx.moveTo(x, floorY); ctx.lineTo(x - 8, floorY + 12); ctx.stroke();
    }

    const bx    = state.get('block_x') || w / 2;
    const blockY = floorY - 28;
    const r      = 26;

    // Shadow
    ctx.fillStyle = 'rgba(0,0,0,0.08)';
    ctx.beginPath(); ctx.ellipse(bx, floorY + 4, r + 4, 5, 0, 0, Math.PI * 2); ctx.fill();

    // Block
    const blockGrad = ctx.createLinearGradient(bx - r, blockY - r, bx + r, blockY + r);
    blockGrad.addColorStop(0, '#818cf8'); blockGrad.addColorStop(1, '#4f46e5');
    ctx.fillStyle = blockGrad; ctx.shadowBlur = 14; ctx.shadowColor = 'rgba(99,102,241,0.4)';
    ctx.beginPath(); ctx.roundRect(bx - r, blockY - r, r * 2, r * 2, 6); ctx.fill();
    ctx.shadowBlur = 0;
    const mass = state.get('mass') || 5;
    ctx.fillStyle = '#fff'; ctx.font = 'bold 11px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(mass + ' kg', bx, blockY + 4);

    const sc       = 0.6;
    const applied  = state.get('applied_force')  || 0;
    const friction = state.get('friction_force') || 0;
    const vel      = state.get('velocity')       || 0;

    // Applied force arrow
    if (Math.abs(applied) > 0.5) {
      const dir = applied > 0 ? 1 : -1;
      const len = Math.abs(applied) * sc;
      ctx.strokeStyle = '#22c55e'; ctx.lineWidth = 3; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(bx, blockY); ctx.lineTo(bx + applied * sc, blockY); ctx.stroke();
      ctx.fillStyle = '#22c55e';
      ctx.beginPath();
      ctx.moveTo(bx + applied * sc, blockY - 6);
      ctx.lineTo(bx + applied * sc + dir * 10, blockY);
      ctx.lineTo(bx + applied * sc, blockY + 6);
      ctx.closePath(); ctx.fill();
      ctx.font = 'bold 9px sans-serif'; ctx.fillStyle = '#166534'; ctx.textAlign = 'center';
      ctx.fillText('F=' + applied.toFixed(0) + 'N', bx + applied * sc * 0.5, blockY - 14);
    }

    // Friction arrow (only when moving)
    if (Math.abs(vel) > 0.01 && Math.abs(friction) > 0.5) {
      const flen = Math.abs(friction) * sc * 0.5;
      const dir  = friction > 0 ? 1 : -1;
      ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.moveTo(bx, blockY + 10); ctx.lineTo(bx + friction * sc * 0.5, blockY + 10); ctx.stroke();
      ctx.fillStyle = '#ef4444'; ctx.font = '8px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText('f=' + Math.abs(friction).toFixed(0) + 'N', bx + friction * sc * 0.25, blockY + 24);
    }

    // Normal & Weight (dashed)
    ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 1.5; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(bx - 22, blockY - r - 5); ctx.lineTo(bx + 22, blockY - r - 5); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(bx - 22, blockY + r + 5); ctx.lineTo(bx + 22, blockY + r + 5); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#92400e'; ctx.font = '8px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('N=' + (state.get('normal_force') || 0).toFixed(0) + 'N', bx + 30, blockY - r - 1);
    ctx.fillText('W=' + (state.get('weight')       || 0).toFixed(0) + 'N', bx + 30, blockY + r + 11);

    // HUD
    ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.beginPath(); ctx.roundRect(8, 8, 200, 80, 8); ctx.fill();
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('F_net = ' + (state.get('net_force')    || 0).toFixed(1) + ' N',   16, 28);
    ctx.fillText('a     = ' + (state.get('acceleration') || 0).toFixed(2) + ' m/s²',16, 46);
    ctx.fillText('v     = ' + (state.get('velocity')     || 0).toFixed(2) + ' m/s', 16, 64);
    ctx.fillStyle = '#6366f1'; ctx.font = '9px sans-serif';
    ctx.fillText('F = ma', 16, 80);
    ctx.textAlign = 'right'; ctx.fillStyle = '#475569';
    ctx.fillText('Click to set force →', w - 10, h - 10);
  }
}
"""


# ══════════════════════════════════════════════════════════════════════════
#  ENERGY (Pendulum)
# ══════════════════════════════════════════════════════════════════════════

ENERGY_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.theta  = Math.PI / 4;
    this.omega  = 0;
    this.time   = 0;
  }

  update(dt, state) {
    this.time += dt;
    const mass   = state.get('mass')   || 1;
    const length = state.get('length') || 1;
    const g      = state.get('gravity')|| 9.81;
    const damp   = 0.005;

    // Euler integration of pendulum ODE: θ'' = -(g/L)sinθ - b·θ'
    const alpha    = -(g / length) * Math.sin(this.theta) - damp * this.omega;
    this.omega    += alpha * dt;
    this.theta    += this.omega * dt;

    const h        = length * (1 - Math.cos(this.theta));
    const pe       = mass * g * h;
    const ke       = 0.5 * mass * (length * this.omega) ** 2;

    state.set('theta',       parseFloat((this.theta * 180 / Math.PI).toFixed(2)));
    state.set('omega',       parseFloat(this.omega.toFixed(3)));
    state.set('pe',          parseFloat(pe.toFixed(3)));
    state.set('ke',          parseFloat(ke.toFixed(3)));
    state.set('total_energy',parseFloat((pe + ke).toFixed(3)));
    state.set('period',      parseFloat((2 * Math.PI * Math.sqrt(length / g)).toFixed(3)));
  }

  onReset() { this.theta = Math.PI / 4; this.omega = 0; this.time = 0; }

  canvasInteractions(canvas, state, bus) {
    const self = this;
    canvas.addEventListener('click', function(e) {
      const rect  = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      const cx    = (e.clientX - rect.left) * scaleX - canvas.width / 2;
      const cy    = (e.clientY - rect.top)  * scaleY - 40;
      self.theta  = Math.atan2(cx, cy);
      self.omega  = 0;
    });
  }

  getHint() { return 'Click on canvas to set pendulum start angle'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
    this._trail = [];
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
    bgGrad.addColorStop(0, '#f0f9ff'); bgGrad.addColorStop(1, '#f8fafc');
    ctx.fillStyle = bgGrad; ctx.fillRect(0, 0, w, h);

    const engine = window._engine;
    if (!engine) return;

    const length    = state.get('length')  || 1;
    const pivX      = w / 2, pivY = 50;
    const pxLen     = Math.min(h - 90, length * 180);
    const theta     = engine.theta;
    const bobX      = pivX + pxLen * Math.sin(theta);
    const bobY      = pivY + pxLen * Math.cos(theta);

    // Trail
    this._trail.push({ x: bobX, y: bobY });
    if (this._trail.length > 120) this._trail.shift();
    if (this._trail.length > 1) {
      ctx.strokeStyle = 'rgba(139,92,246,0.25)'; ctx.lineWidth = 2;
      ctx.beginPath();
      this._trail.forEach(function(p, i) { if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y); });
      ctx.stroke();
    }

    // String
    ctx.strokeStyle = '#64748b'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(pivX, pivY); ctx.lineTo(bobX, bobY); ctx.stroke();

    // Pivot
    ctx.fillStyle = '#334155';
    ctx.beginPath(); ctx.arc(pivX, pivY, 7, 0, Math.PI * 2); ctx.fill();

    // Rest position line
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1; ctx.setLineDash([5, 4]);
    ctx.beginPath(); ctx.moveTo(pivX, pivY); ctx.lineTo(pivX, pivY + pxLen); ctx.stroke(); ctx.setLineDash([]);

    // Energy bar background
    const barX = 12, barY = h - 70, barW = 120, barH = 18;
    ctx.fillStyle = '#e2e8f0'; ctx.beginPath(); ctx.roundRect(barX, barY, barW, barH, 4); ctx.fill();
    ctx.fillStyle = '#e2e8f0'; ctx.beginPath(); ctx.roundRect(barX, barY + 24, barW, barH, 4); ctx.fill();

    const te  = (state.get('total_energy') || 0.001);
    const pe  = state.get('pe') || 0;
    const ke  = state.get('ke') || 0;
    const peW = Math.min(barW, (pe / te) * barW);
    const keW = Math.min(barW, (ke / te) * barW);

    ctx.fillStyle = '#f59e0b';
    ctx.beginPath(); ctx.roundRect(barX, barY, peW, barH, 4); ctx.fill();
    ctx.fillStyle = '#6366f1';
    ctx.beginPath(); ctx.roundRect(barX, barY + 24, keW, barH, 4); ctx.fill();

    ctx.fillStyle = '#374151'; ctx.font = 'bold 9px sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('PE: ' + pe.toFixed(3) + ' J', barX, barY - 4);
    ctx.fillText('KE: ' + ke.toFixed(3) + ' J', barX, barY + 20);

    // Bob
    const mass   = state.get('mass') || 1;
    const bobR   = 10 + mass * 3;
    const bobGrad = ctx.createRadialGradient(bobX - 3, bobY - 3, 1, bobX, bobY, bobR);
    bobGrad.addColorStop(0, '#c4b5fd'); bobGrad.addColorStop(1, '#7c3aed');
    ctx.shadowBlur = 16; ctx.shadowColor = 'rgba(124,58,237,0.5)';
    ctx.fillStyle = bobGrad;
    ctx.beginPath(); ctx.arc(bobX, bobY, bobR, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#fff'; ctx.font = 'bold 9px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(mass + 'kg', bobX, bobY + 3);

    // HUD
    ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.beginPath(); ctx.roundRect(w - 175, 8, 165, 78, 8); ctx.fill();
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('θ = ' + (state.get('theta')  || 0).toFixed(1) + '°',   w - 165, 28);
    ctx.fillText('ω = ' + (state.get('omega')  || 0).toFixed(3) + ' r/s', w - 165, 46);
    ctx.fillText('T = ' + (state.get('period') || 0) + ' s',               w - 165, 64);
    ctx.textAlign = 'left';
  }
}
"""


# ══════════════════════════════════════════════════════════════════════════
#  BUOYANCY
# ══════════════════════════════════════════════════════════════════════════

BUOYANCY_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.blockY   = 0;   // pixels from top, 0 = water surface
    this.blockVy  = 0;
    this.settled  = false;
  }

  update(dt, state) {
    const mass    = state.get('mass')         || 1;
    const volume  = state.get('volume')       || 0.001;
    const rhoFluid= state.get('fluid_density')|| 1000;
    const g       = state.get('gravity')      || 9.81;

    const rhoObj   = mass / volume;
    const weight   = mass * g;
    const buoyant  = rhoFluid * volume * g;
    const net      = weight - buoyant;
    const subFrac  = Math.min(1, Math.max(0, rhoObj / rhoFluid));

    state.set('weight',           parseFloat(weight.toFixed(3)));
    state.set('buoyant_force',    parseFloat(buoyant.toFixed(3)));
    state.set('net_force',        parseFloat(net.toFixed(3)));
    state.set('density_ratio',    parseFloat((rhoObj / rhoFluid).toFixed(3)));
    state.set('submerged_fraction',parseFloat(subFrac.toFixed(3)));
    state.set('object_density',   parseFloat(rhoObj.toFixed(1)));

    if (!this.settled) {
      const accel  = net / mass;
      this.blockVy += accel * dt * 0.3;
      this.blockVy *= 0.92;
      this.blockY  += this.blockVy * dt;

      // Equilibrium depth (positive blockY = submerged below surface)
      const eqDepth = (rhoObj / rhoFluid) * this.canvas.height * 0.3;
      this.blockY   = Math.max(-40, Math.min(this.canvas.height * 0.5, this.blockY));

      if (Math.abs(this.blockVy) < 0.05 && Math.abs(this.blockY - eqDepth) < 2) {
        this.settled = true;
        this.blockY  = eqDepth;
      }
    }
  }

  onReset() { this.blockY = 0; this.blockVy = 0; this.settled = false; }
  getHint()  { return 'Change mass or volume to see whether the object floats, sinks or is neutral'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Sky
    ctx.fillStyle = '#f0f9ff'; ctx.fillRect(0, 0, w, h);

    const waterY = h * 0.38;  // water surface y

    // Water body
    const waterGrad = ctx.createLinearGradient(0, waterY, 0, h);
    waterGrad.addColorStop(0, 'rgba(56,189,248,0.7)');
    waterGrad.addColorStop(1, 'rgba(14,116,144,0.8)');
    ctx.fillStyle = waterGrad; ctx.fillRect(0, waterY, w, h - waterY);

    // Water ripple at surface
    ctx.strokeStyle = 'rgba(255,255,255,0.5)'; ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let x = 0; x <= w; x += 3) {
      const wy = waterY + 2 * Math.sin(x * 0.05 + performance.now() * 0.002);
      if (x === 0) ctx.moveTo(x, wy); else ctx.lineTo(x, wy);
    }
    ctx.stroke();

    // Object block
    const engine = window._engine;
    if (!engine) return;

    const rhoObj   = state.get('object_density')    || 1000;
    const rhoFluid = state.get('fluid_density')      || 1000;
    const subFrac  = state.get('submerged_fraction') || 0;

    const blockSize = 52;
    const bx  = w / 2 - blockSize / 2;
    // engine.blockY: 0 = water surface, positive = sinks
    const by  = waterY - blockSize + engine.blockY;

    // Colour by density
    const ratio = rhoObj / rhoFluid;
    const r = Math.min(255, Math.round(ratio * 220));
    const b = Math.round(Math.max(50, 220 - ratio * 180));
    ctx.fillStyle = `rgb(${r}, 100, ${b})`;
    ctx.shadowBlur = 12; ctx.shadowColor = 'rgba(0,0,0,0.25)';
    ctx.beginPath(); ctx.roundRect(bx, by, blockSize, blockSize, 6); ctx.fill();
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#fff'; ctx.font = 'bold 9px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText((rhoObj).toFixed(0) + ' kg/m³', w / 2, by + blockSize / 2 + 3);

    // Force arrows (scaled)
    const sc      = 0.015;
    const weight  = state.get('weight')        || 0;
    const buoyant = state.get('buoyant_force') || 0;
    const midX    = w / 2;
    const midY    = by + blockSize / 2;

    // Weight ↓
    if (weight > 0) {
      const wLen = weight * sc;
      ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 3; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(midX, midY + blockSize / 2 + 2); ctx.lineTo(midX, midY + blockSize / 2 + 2 + wLen); ctx.stroke();
      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.moveTo(midX - 6, midY + blockSize / 2 + wLen - 2);
      ctx.lineTo(midX,     midY + blockSize / 2 + wLen + 12);
      ctx.lineTo(midX + 6, midY + blockSize / 2 + wLen - 2);
      ctx.closePath(); ctx.fill();
      ctx.font = '9px sans-serif'; ctx.fillStyle = '#7f1d1d'; ctx.textAlign = 'left';
      ctx.fillText('W=' + weight.toFixed(1) + 'N', midX + 8, midY + blockSize / 2 + wLen / 2);
    }

    // Buoyancy ↑
    if (buoyant > 0 && subFrac > 0) {
      const bLen = buoyant * sc;
      ctx.strokeStyle = '#0ea5e9'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(midX - 18, midY - blockSize / 2 - 2); ctx.lineTo(midX - 18, midY - blockSize / 2 - 2 - bLen); ctx.stroke();
      ctx.fillStyle = '#0ea5e9';
      ctx.beginPath();
      ctx.moveTo(midX - 24, midY - blockSize / 2 - bLen + 2);
      ctx.lineTo(midX - 18, midY - blockSize / 2 - bLen - 12);
      ctx.lineTo(midX - 12, midY - blockSize / 2 - bLen + 2);
      ctx.closePath(); ctx.fill();
      ctx.font = '9px sans-serif'; ctx.fillStyle = '#075985'; ctx.textAlign = 'right';
      ctx.fillText('B=' + buoyant.toFixed(1) + 'N', midX - 26, midY - blockSize / 2 - bLen / 2);
    }

    // Status label
    const statusColor = ratio < 0.98 ? '#059669' : (ratio > 1.02 ? '#dc2626' : '#d97706');
    const statusText  = ratio < 0.98 ? 'FLOATING' : (ratio > 1.02 ? 'SINKING'  : 'NEUTRAL');
    ctx.fillStyle = statusColor; ctx.font = 'bold 14px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(statusText, w / 2, waterY - 14);

    // HUD
    ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.beginPath(); ctx.roundRect(8, 8, 200, 96, 8); ctx.fill();
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('W  = ' + (state.get('weight')        || 0).toFixed(2) + ' N',   16, 28);
    ctx.fillText('B  = ' + (state.get('buoyant_force') || 0).toFixed(2) + ' N',   16, 46);
    ctx.fillText('ρ_obj = ' + (state.get('object_density')||0).toFixed(0) + ' kg/m³', 16, 64);
    ctx.fillText('ratio = ' + (state.get('density_ratio') || 0).toFixed(3),       16, 82);
    ctx.fillStyle = '#475569'; ctx.font = '9px sans-serif';
    ctx.fillText('B = ρ_f · V · g', 16, 98);
  }
}
"""


# ══════════════════════════════════════════════════════════════════════════
#  OPTICS & LENS MAGNIFICATION
# ══════════════════════════════════════════════════════════════════════════

OPTICS_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas;
    this.state = state;
    this.bus = bus;
    this.time = 0;
    this.dragging = null;
    this._bound = false;
    
    // Register slider listener callbacks via EventBus
    this.bus.on('change:focal_length', () => {
      // Only set if not currently dragging focal point on canvas
      if (this.dragging !== 'focal') {
        this.state.set('_last_changed', 'focal_length');
      }
    });
    this.bus.on('change:lens_power', () => {
      if (this.dragging !== 'focal') {
        this.state.set('_last_changed', 'lens_power');
      }
    });
    
    this.canvasInteractions(canvas, state, bus);
  }

  update(dt, state) {
    this.time += dt;

    const ho = Math.max(0.01, Math.min(0.2, +state.get('object_height') || 0.05));
    const do_ = Math.max(0.06, Math.min(1.5, +state.get('object_distance') || 0.3));
    let f = Math.max(0.05, Math.min(0.5, +state.get('focal_length') || 0.1));
    let P = +state.get('lens_power') || 10.0;

    // Handle interactive parameter coupling
    const lastChanged = state.get('_last_changed');
    if (lastChanged === 'focal_length') {
      const targetP = 1 / f;
      if (Math.abs(P - targetP) > 0.01) {
        P = targetP;
        state.set('lens_power', parseFloat(P.toFixed(1)));
        const pEl = document.getElementById('lens_power');
        if (pEl) pEl.value = P.toFixed(1);
        const pBg = document.getElementById('badge-lens_power');
        if (pBg) pBg.textContent = P.toFixed(1);
      }
    } else if (lastChanged === 'lens_power') {
      const targetF = 1 / P;
      if (Math.abs(f - targetF) > 0.001) {
        f = targetF;
        state.set('focal_length', parseFloat(f.toFixed(3)));
        const fEl = document.getElementById('focal_length');
        if (fEl) fEl.value = f.toFixed(3);
        const fBg = document.getElementById('badge-focal_length');
        if (fBg) fBg.textContent = f.toFixed(2);
      }
    }

    state.set('_last_changed', null); // clear trigger

    const invF = 1 / f;
    const invDo = 1 / do_;
    const invDi = invF - invDo;

    let di;
    if (Math.abs(invDi) < 1e-9) {
      di = invDi >= 0 ? 1e6 : -1e6; // infinity
    } else {
      di = 1 / invDi;
    }

    const m = -di / do_;
    const hi = m * ho;

    const imageType = di > 0 ? 'real' : 'virtual';
    const orientation = hi >= 0 ? 'upright' : 'inverted';

    state.set('image_distance', di);
    state.set('image_height', hi);
    state.set('magnification', m);
    state.set('image_type', imageType);
    state.set('image_orientation', orientation);
  }

  onReset() {
    this.time = 0;
  }

  getHint() {
    return 'Drag the green Object arrow or yellow Focal point directly on the canvas to adjust parameters!';
  }

  canvasInteractions(canvas, state, bus) {
    if (this._bound) return;
    this._bound = true;

    const getPos = (e) => {
      const rect = canvas.getBoundingClientRect();
      const t = e.touches && e.touches[0] ? e.touches[0] : e;
      return {
        x: (t.clientX - rect.left) * (canvas.width / rect.width),
        y: (t.clientY - rect.top) * (canvas.height / rect.height)
      };
    };

    const onDown = (e) => {
      const p = getPos(e);
      const cx = canvas.width * 0.5;
      const cy = canvas.height * 0.55;
      
      const do_ = state.get('object_distance') || 0.3;
      const ho = state.get('object_height') || 0.05;
      const f = state.get('focal_length') || 0.1;
      
      const di = state.get('image_distance') || 0;
      const maxD = Math.max(do_, f, Math.abs(di) < 1.5 ? Math.abs(di) : 0);
      const scale = Math.min(300, (canvas.width * 0.4) / Math.max(0.2, maxD));

      const objX = cx - do_ * scale;
      const objY = cy - ho * scale;
      const f1x = cx - f * scale;

      const distToObj = Math.hypot(p.x - objX, p.y - objY);
      const distToF = Math.hypot(p.x - f1x, p.y - cy);

      if (distToObj < 25) {
        this.dragging = 'object';
        canvas.style.cursor = 'grabbing';
        e.preventDefault();
      } else if (distToF < 20) {
        this.dragging = 'focal';
        canvas.style.cursor = 'grabbing';
        e.preventDefault();
      }
    };

    const onMove = (e) => {
      const p = getPos(e);
      const cx = canvas.width * 0.5;
      const cy = canvas.height * 0.55;
      
      const do_ = state.get('object_distance') || 0.3;
      const f = state.get('focal_length') || 0.1;
      const di = state.get('image_distance') || 0;
      const maxD = Math.max(do_, f, Math.abs(di) < 1.5 ? Math.abs(di) : 0);
      const scale = Math.min(300, (canvas.width * 0.4) / Math.max(0.2, maxD));

      if (!this.dragging) {
        const objX = cx - do_ * scale;
        const ho = state.get('object_height') || 0.05;
        const objY = cy - ho * scale;
        const f1x = cx - f * scale;
        
        const distToObj = Math.hypot(p.x - objX, p.y - objY);
        const distToF = Math.hypot(p.x - f1x, p.y - cy);
        
        if (distToObj < 20 || distToF < 15) {
          canvas.style.cursor = 'grab';
        } else {
          canvas.style.cursor = 'crosshair';
        }
        return;
      }

      if (this.dragging === 'object') {
        const targetDo = (cx - p.x) / scale;
        const targetHo = (cy - p.y) / scale;
        
        const clampedDo = Math.max(0.06, Math.min(1.5, targetDo));
        const clampedHo = Math.max(0.01, Math.min(0.2, targetHo));
        
        state.set('object_distance', clampedDo);
        state.set('object_height', clampedHo);
        
        const doEl = document.getElementById('object_distance');
        if (doEl) doEl.value = clampedDo.toFixed(2);
        const doBg = document.getElementById('badge-object_distance');
        if (doBg) doBg.textContent = clampedDo.toFixed(2);
        
        const hoEl = document.getElementById('object_height');
        if (hoEl) hoEl.value = clampedHo.toFixed(3);
        const hoBg = document.getElementById('badge-object_height');
        if (hoBg) hoBg.textContent = clampedHo.toFixed(2);
        
      } else if (this.dragging === 'focal') {
        const targetF = (cx - p.x) / scale;
        const clampedF = Math.max(0.05, Math.min(0.5, targetF));
        
        state.set('focal_length', clampedF);
        state.set('_last_changed', 'focal_length');
        
        const fEl = document.getElementById('focal_length');
        if (fEl) fEl.value = clampedF.toFixed(3);
        const fBg = document.getElementById('badge-focal_length');
        if (fBg) fBg.textContent = clampedF.toFixed(2);
      }
      e.preventDefault();
    };

    const onUp = () => {
      this.dragging = null;
      canvas.style.cursor = 'crosshair';
    };

    canvas.addEventListener('mousedown', onDown);
    canvas.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);

    canvas.addEventListener('touchstart', onDown, { passive: false });
    canvas.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend', onUp);
  }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.state = state;
    this.bus = bus;
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Light premium gradient background
    const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
    bgGrad.addColorStop(0, '#ffffff');
    bgGrad.addColorStop(1, '#f8fafc');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    // Draw grid in soft blue-grey
    ctx.strokeStyle = 'rgba(24, 0, 173, 0.04)';
    ctx.lineWidth = 1.0;
    for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    const ho = Math.max(0.01, +state.get('object_height') || 0.05);
    const do_ = Math.max(0.06, +state.get('object_distance') || 0.3);
    const f = Math.max(0.05, +state.get('focal_length') || 0.1);
    const P = +state.get('lens_power') || (1 / f); // Correctly define P to prevent ReferenceError
    const di = +state.get('image_distance') || 0;
    const hi = +state.get('image_height') || 0;
    const m = +state.get('magnification') || 0;
    const imageType = state.get('image_type') || (di > 0 ? 'real' : 'virtual');

    const cx = w * 0.5;
    const cy = h * 0.55;

    // Dynamic Scale Calculation to keep everything on canvas
    const maxD = Math.max(do_, f, Math.abs(di) < 1.5 ? Math.abs(di) : 0);
    const scale = Math.min(300, (w * 0.4) / Math.max(0.2, maxD));

    const lensX = cx;
    const objX = lensX - do_ * scale;
    const objY = cy - ho * scale;
    const imgX = lensX + di * scale;
    const imgY = cy - hi * scale;

    const f1x = lensX - f * scale; // left F
    const f2x = lensX + f * scale; // right F'

    // 1. Draw Optical Axis
    ctx.save();
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(20, cy);
    ctx.lineTo(w - 20, cy);
    ctx.stroke();

    // Tick marks on Axis
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.3)';
    ctx.lineWidth = 1;
    ctx.fillStyle = '#64748b';
    ctx.font = '9px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    for (let offset = -1.0; offset <= 1.0; offset += 0.2) {
      if (Math.abs(offset) < 0.01) continue;
      const tx = cx + offset * scale;
      if (tx > 20 && tx < w - 20) {
        ctx.beginPath();
        ctx.moveTo(tx, cy - 5);
        ctx.lineTo(tx, cy + 5);
        ctx.stroke();
        ctx.fillText(offset.toFixed(1) + 'm', tx, cy + 16);
      }
    }
    ctx.restore();

    // 2. Draw Focal Points
    ctx.save();
    ctx.fillStyle = '#d97706';
    ctx.shadowBlur = 0;
    [f1x, f2x].forEach((x, i) => {
      if (x > 20 && x < w - 20) {
        ctx.beginPath();
        ctx.arc(x, cy, 5.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#d97706';
        ctx.font = 'bold 11px sans-serif';
        ctx.fillText(i === 0 ? 'F' : "F'", x - 5, cy - 12);
      }
    });
    ctx.restore();

    // Pulse time factor
    const time = window._engine ? window._engine.time : 0;
    const pulseProgress = (time * 0.45) % 1.0;

    // 3. Draw Rays helper
    const drawRay = (pts, color, isDashed) => {
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.0;
      ctx.shadowBlur = 0;
      if (isDashed) ctx.setLineDash([6, 5]);
      ctx.beginPath();
      pts.forEach((p, i) => {
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
      ctx.stroke();
      ctx.restore();

      // Draw pulse dot along ray
      if (pts.length >= 2) {
        let totalLen = 0;
        let segmentLens = [];
        for (let i = 0; i < pts.length - 1; i++) {
          const l = Math.hypot(pts[i+1].x - pts[i].x, pts[i+1].y - pts[i].y);
          totalLen += l;
          segmentLens.push(l);
        }
        let targetL = totalLen * pulseProgress;
        let currentL = 0;
        let px = pts[0].x, py = pts[0].y;
        for (let i = 0; i < pts.length - 1; i++) {
          if (targetL <= currentL + segmentLens[i]) {
            const ratio = (targetL - currentL) / segmentLens[i];
            px = pts[i].x + (pts[i+1].x - pts[i].x) * ratio;
            py = pts[i].y + (pts[i+1].y - pts[i].y) * ratio;
            break;
          }
          currentL += segmentLens[i];
        }
        ctx.save();
        ctx.fillStyle = color;
        ctx.shadowBlur = 0;
        ctx.beginPath();
        ctx.arc(px, py, 4.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    };

    // 4. Principal Ray 1: Parallel to axis, refracts through F'
    const ray1_pts = [
      { x: objX, y: objY },
      { x: lensX, y: objY }
    ];
    if (imageType === 'real') {
      ray1_pts.push({ x: f2x, y: cy });
      if (isFinite(imgX)) ray1_pts.push({ x: imgX, y: imgY });
    } else {
      const dx = w - lensX;
      const dy = ((cy - objY) / f) * dx;
      ray1_pts.push({ x: w, y: cy + dy });
      if (isFinite(imgX)) {
        drawRay([
          { x: lensX, y: objY },
          { x: imgX, y: imgY }
        ], '#0ea5e9', true);
      }
    }
    drawRay(ray1_pts, '#0ea5e9', false);

    // 5. Principal Ray 2: Through optical center (lensX, cy)
    const ray2_pts = [
      { x: objX, y: objY },
      { x: lensX, y: cy }
    ];
    if (isFinite(imgX)) {
      ray2_pts.push({ x: imgX, y: imgY });
    } else {
      const dx = w - objX;
      const dy = (cy - objY) / (lensX - objX) * dx;
      ray2_pts.push({ x: objX + dx, y: objY + dy });
    }
    if (imageType === 'virtual' && isFinite(imgX)) {
      drawRay([
        { x: lensX, y: cy },
        { x: imgX, y: imgY }
      ], '#059669', true);
    }
    drawRay(ray2_pts, '#059669', false);

    // 6. Principal Ray 3: Through left focal point F, refracts parallel
    const ray3_pts = [];
    if (do_ > f) {
      ray3_pts.push({ x: objX, y: objY });
      ray3_pts.push({ x: lensX, y: imgY });
      if (isFinite(imgX)) ray3_pts.push({ x: imgX, y: imgY });
      drawRay(ray3_pts, '#7c3aed', false);
    } else {
      const slope = (objY - cy) / (objX - f1x);
      const lensY = cy + slope * (lensX - f1x);
      ray3_pts.push({ x: objX, y: objY });
      ray3_pts.push({ x: lensX, y: lensY });
      ray3_pts.push({ x: w, y: lensY });
      
      drawRay(ray3_pts, '#7c3aed', false);
      if (isFinite(imgX)) {
        drawRay([
          { x: lensX, y: lensY },
          { x: imgX, y: imgY }
        ], '#7c3aed', true);
      }
    }

    // 7. Draw the Lens (convex)
    const drawConvexLens = () => {
      const grad = ctx.createLinearGradient(lensX - 16, 0, lensX + 16, 0);
      grad.addColorStop(0, 'rgba(24, 0, 173, 0.08)');
      grad.addColorStop(0.5, 'rgba(24, 0, 173, 0.2)');
      grad.addColorStop(1, 'rgba(24, 0, 173, 0.08)');
      ctx.save();
      ctx.fillStyle = grad;
      ctx.strokeStyle = '#1800ad';
      ctx.lineWidth = 2.5;
      ctx.shadowBlur = 0;
      ctx.beginPath();
      ctx.moveTo(lensX, cy - 130);
      ctx.quadraticCurveTo(lensX + 22, cy, lensX, cy + 130);
      ctx.quadraticCurveTo(lensX - 22, cy, lensX, cy - 130);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Glare lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(lensX - 100, cy - 40, 110, -0.4, 0.4);
      ctx.stroke();
      ctx.restore();
    };
    drawConvexLens();

    // 8. Draw Object Arrow
    const drawArrow = (x, baseY, height, color, label, isInteractive) => {
      ctx.save();
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = 4.5;
      ctx.lineCap = 'round';
      ctx.shadowBlur = 0;
      
      ctx.beginPath();
      ctx.moveTo(x, baseY);
      ctx.lineTo(x, baseY - height);
      ctx.stroke();
      
      const tipY = baseY - height;
      const dir = height >= 0 ? -1 : 1;
      ctx.beginPath();
      ctx.moveTo(x, tipY);
      ctx.lineTo(x - 9, tipY + 13 * dir);
      ctx.lineTo(x + 9, tipY + 13 * dir);
      ctx.closePath();
      ctx.fill();
      
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#1e293b';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(label, x, baseY - height - 12 * dir);
      ctx.restore();

      if (isInteractive) {
        const isHover = window._engine && window._engine.dragging === 'object';
        ctx.save();
        ctx.strokeStyle = isHover ? '#059669' : 'rgba(5, 150, 105, 0.4)';
        ctx.lineWidth = 2;
        ctx.setLineDash(isHover ? [] : [4, 3]);
        ctx.beginPath();
        ctx.arc(x, tipY, 14 + (isHover ? 0 : 2 * Math.sin(performance.now() * 0.007)), 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }
    };

    drawArrow(objX, cy, ho * scale, '#059669', 'OBJECT (h_o)', true);

    // 9. Draw Image Arrow
    const imgVisible = isFinite(di) && Math.abs(di) < 1e5;
    if (imgVisible) {
      const isReal = imageType === 'real';
      const label = isReal ? 'REAL IMAGE (h_i)' : 'VIRTUAL IMAGE (h_i)';
      const color = isReal ? '#dc2626' : '#7c3aed';
      drawArrow(imgX, cy, hi * scale, color, label, false);
    }

    // 10. Draw Eye for Virtual Image
    if (imageType === 'virtual') {
      const eyeX = w - 45;
      const eyeY = cy;
      ctx.save();
      ctx.strokeStyle = '#94a3b8';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(eyeX - 18, eyeY);
      ctx.quadraticCurveTo(eyeX, eyeY - 11, eyeX + 18, eyeY);
      ctx.quadraticCurveTo(eyeX, eyeY + 11, eyeX - 18, eyeY);
      ctx.stroke();
      ctx.fillStyle = '#0ea5e9';
      ctx.beginPath();
      ctx.arc(eyeX, eyeY, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#1e293b';
      ctx.beginPath();
      ctx.arc(eyeX, eyeY, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    // 11. HUD Info Panel
    ctx.save();
    const hudX = 18, hudY = 18, hudW = 260, hudH = 105;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
    ctx.strokeStyle = 'rgba(24, 0, 173, 0.15)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(hudX, hudY, hudW, hudH, 12);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#1800ad';
    ctx.font = 'bold 11px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText('LENS PARAMETERS & MATH', hudX + 14, hudY + 20);

    ctx.strokeStyle = 'rgba(24, 0, 173, 0.1)';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(hudX + 14, hudY + 28);
    ctx.lineTo(hudX + hudW - 14, hudY + 28);
    ctx.stroke();

    ctx.font = '11px "JetBrains Mono", monospace';
    const lines = [
      `Object:   d_o = ${do_.toFixed(3)} m,  h_o = ${ho.toFixed(3)} m`,
      `Lens:     f   = ${f.toFixed(3)} m,  P   = ${P.toFixed(2)} D`,
      `Image:    d_i = ${imgVisible ? di.toFixed(3) : '∞'} m,  h_i = ${imgVisible ? hi.toFixed(3) : '∞'} m`,
      `Magnify:  m   = ${imgVisible ? m.toFixed(3) : '∞'}  (${imageType.toUpperCase()})`
    ];
    let lineY = hudY + 44;
    lines.forEach((l, idx) => {
      if (idx === 0) ctx.fillStyle = '#047857';
      else if (idx === 1) ctx.fillStyle = '#1800ad';
      else if (idx === 2) ctx.fillStyle = imageType === 'real' ? '#b91c1c' : '#6d28d9';
      else if (idx === 3) ctx.fillStyle = '#047857';
      else ctx.fillStyle = '#334155';
      ctx.fillText(l, hudX + 14, lineY);
      lineY += 14;
    });
    ctx.restore();
  }
}
"""

def _build_optics(spec: SimulationSpecification) -> str:
    # Ensure standard parameters exist to match sliders and bindings perfectly
    from app.simulation_engine.schemas import SimulationParameter
    required_params = [
        {"id": "object_distance", "name": "Object Distance", "symbol": "d_o", "min": 0.06, "max": 1.5, "default": 0.3, "step": 0.01, "unit": "m", "description": "Object distance from lens"},
        {"id": "object_height", "name": "Object Height", "symbol": "h_o", "min": 0.01, "max": 0.2, "default": 0.05, "step": 0.005, "unit": "m", "description": "Object height"},
        {"id": "focal_length", "name": "Focal Length", "symbol": "f", "min": 0.05, "max": 0.5, "default": 0.1, "step": 0.005, "unit": "m", "description": "Focal length"},
        {"id": "lens_power", "name": "Lens Power", "symbol": "P", "min": 2.0, "max": 20.0, "default": 10.0, "step": 0.1, "unit": "D", "description": "Lens power (1/f)"}
    ]
    spec.parameters = [
        SimulationParameter(
            id=p["id"],
            name=p["name"],
            symbol=p["symbol"],
            min=p["min"],
            max=p["max"],
            default=p["default"],
            step=p["step"],
            unit=p["unit"],
            description=p["description"],
            type="number"
        ) for p in required_params
    ]

    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Object Distance (d_o) <span class="ctrl-unit">m</span></span>
        <span class="val-badge" id="badge-object_distance">0.30</span>
      </div>
      <input type="range" id="object_distance" min="0.06" max="1.50" step="0.01" value="0.30">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Object Height (h_o) <span class="ctrl-unit">m</span></span>
        <span class="val-badge" id="badge-object_height">0.05</span>
      </div>
      <input type="range" id="object_height" min="0.01" max="0.20" step="0.005" value="0.05">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Focal Length (f) <span class="ctrl-unit">m</span></span>
        <span class="val-badge" id="badge-focal_length">0.10</span>
      </div>
      <input type="range" id="focal_length" min="0.05" max="0.50" step="0.005" value="0.10">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Lens Power (P) <span class="ctrl-unit">D</span></span>
        <span class="val-badge" id="badge-lens_power">10.0</span>
      </div>
      <input type="range" id="lens_power" min="2.0" max="20.0" step="0.1" value="10.0">
    </div>"""

    values = """    <div class="vcard"><div class="lbl">Image Dist (d_i)</div><div class="num" id="val-image_distance" style="color:#ef4444">0.150 m</div></div>
    <div class="vcard"><div class="lbl">Image H (h_i)</div><div class="num" id="val-image_height" style="color:#8b5cf6">-0.025 m</div></div>
    <div class="vcard"><div class="lbl">Magnification</div><div class="num" id="val-magnification" style="color:#34d399">-0.500</div></div>
    <div class="vcard"><div class="lbl">Type</div><div class="num" id="val-image_type" style="color:#38bdf8">REAL</div></div>
    <div class="vcard"><div class="lbl">Orientation</div><div class="num" id="val-image_orientation" style="color:#ec4899">INVERTED</div></div>"""

    presets = """  <div class="presets">
    <button data-do="0.30" data-ho="0.05" data-f="0.10">Real Image (d_o > 2f)</button>
    <button data-do="0.15" data-ho="0.05" data-f="0.10">Magnified Real (f < d_o < 2f)</button>
    <button data-do="0.06" data-ho="0.05" data-f="0.10">Virtual Image (d_o < f)</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var do_ = this.getAttribute('data-do'), ho = this.getAttribute('data-ho'), f = this.getAttribute('data-f');
        function _set(id, val, decimals) {
          var el = document.getElementById(id); if (el) el.value = val;
          var bg = document.getElementById('badge-' + id);
          if (bg) bg.textContent = parseFloat(val).toFixed(decimals);
        }
        _set('object_distance', do_, 2); _set('object_height', ho, 2); _set('focal_length', f, 2);
        _set('lens_power', (1/parseFloat(f)).toFixed(1), 1);
        
        window._state.set('object_distance', parseFloat(do_));
        window._state.set('object_height',   parseFloat(ho));
        window._state.set('focal_length',    parseFloat(f));
        window._state.set('lens_power',      1/parseFloat(f));
        window._state.set('_last_changed',   'focal_length');
      });
    });
"""

    full_script = OPTICS_ENGINE + "\n" + presets_script

    return build_simulation_html(
        spec,
        custom_script  = full_script,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment(spec),
        custom_presets = presets,
    )


def build_physics_simulation(spec: SimulationSpecification) -> str:
    sim_type = spec.simulation_type.value
    topic_lower = spec.topic.lower()

    if any(keyword in topic_lower for keyword in ["lens", "magnification", "optics", "focal length", "spherical lens"]):
        return _build_optics(spec)

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
        return build_simulation_html(spec, custom_script=build_custom_llm_simulation(spec))


# ── per-type builders ───────────────────────────────────────────────────

def _build_projectile_motion(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Launch Angle (θ) <span class="ctrl-unit">deg</span></span>
        <span class="val-badge" id="badge-angle">45</span>
      </div>
      <input type="range" id="angle" min="1" max="89" step="1" value="45"
             aria-label="Launch angle" title="Angle above horizontal in degrees">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Initial Speed (v₀) <span class="ctrl-unit">m/s</span></span>
        <span class="val-badge" id="badge-initial_velocity">20</span>
      </div>
      <input type="range" id="initial_velocity" min="5" max="50" step="1" value="20"
             aria-label="Initial velocity">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Gravity (g) <span class="ctrl-unit">m/s²</span></span>
        <span class="val-badge" id="badge-gravity">9.81</span>
      </div>
      <input type="range" id="gravity" min="0.5" max="30" step="0.1" value="9.81"
             aria-label="Gravitational acceleration">
    </div>"""

    presets = """  <div class="presets">
    <button data-angle="45" data-speed="20" data-gravity="9.81">Earth 45°</button>
    <button data-angle="30" data-speed="30" data-gravity="9.81">Long Range</button>
    <button data-angle="75" data-speed="15" data-gravity="9.81">High Arc</button>
    <button data-angle="45" data-speed="20" data-gravity="1.62">Moon</button>
    <button data-angle="45" data-speed="20" data-gravity="3.72">Mars</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var angle   = this.getAttribute('data-angle');
        var speed   = this.getAttribute('data-speed');
        var gravity = this.getAttribute('data-gravity');
        function _set(id, val) {
          var el = document.getElementById(id); if (el) el.value = val;
          var bg = document.getElementById('badge-' + id); if (bg) bg.textContent = val;
        }
        _set('angle', angle); _set('initial_velocity', speed); _set('gravity', gravity);
        window._state.set('angle',            parseFloat(angle));
        window._state.set('initial_velocity', parseFloat(speed));
        window._state.set('gravity',          parseFloat(gravity));
        var engine = window._engine;
        if (engine && !engine.launched) {
          engine.readyToLaunch = true; engine.trail = []; engine._minPy = undefined;
          engine.px = 70; engine.py = 0;
        }
      });
    });
    // Launch button
    var launchBtn = document.getElementById('launch-btn');
    if (launchBtn) {
      launchBtn.addEventListener('click', function() {
        var engine = window._engine;
        if (engine) {
          engine.launched = false; engine.readyToLaunch = true;
          engine.trail = []; engine._minPy = undefined;
        }
      });
    }
"""

    values = """    <div class="vcard"><div class="lbl">X Pos (m)</div><div class="num" id="val-pos_x" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Y Pos (m)</div><div class="num" id="val-pos_y" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">Time (s)</div><div class="num" id="val-time_of_flight" style="color:#f59e0b">0</div></div>
    <div class="vcard"><div class="lbl">Range (m)</div><div class="num" id="val-range" style="color:#ec4899">0</div></div>
    <div class="vcard"><div class="lbl">Speed (m/s)</div><div class="num" id="val-speed" style="color:#06b6d4">0</div></div>
    <div class="vcard"><div class="lbl">Max H (m)</div><div class="num" id="val-max_height" style="color:#8b5cf6">0</div></div>"""

    graph = """  <div class="graph-area">
    <div class="graph-header">
      <div class="gt">Height vs. Distance</div>
      <div class="gl"><span><span class="dot" style="background:#6366f1"></span>Trajectory</span></div>
    </div>
    <canvas id="graph-canvas" width="700" height="160"></canvas>
  </div>"""

    # Extra launch button inserted into the actions bar via the controls HTML
    launch_btn_html = """
    <div class="actions" style="margin-top:4px">
      <button class="amber" id="launch-btn" style="font-size:13px">🚀 Launch</button>
    </div>"""

    graph_data_push = """
if (graphMgr && state.get('in_flight')) {
  const _px = parseFloat(state.get('pos_x') || 0);
  const _py = parseFloat(state.get('pos_y') || 0);
  graphMgr.setRange(0, Math.max(10, _px * 1.2), 0, Math.max(5, parseFloat(state.get('max_height') || 5) * 1.3));
  graphMgr.pushData('Trajectory', _px, _py);
}
"""

    full_script = PROJECTILE_MOTION_ENGINE + "\n" + presets_script

    return build_simulation_html(
        spec,
        custom_script  = full_script,
        custom_controls= controls + launch_btn_html,
        custom_live_values=values,
        custom_graph   = graph,
        custom_assessment=_build_assessment(spec),
        custom_presets = presets,
    )


def _build_electricity(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Voltage (V) <span class="ctrl-unit">V</span></span>
        <span class="val-badge" id="badge-voltage">5.0</span>
      </div>
      <input type="range" id="voltage" min="1" max="24" step="0.5" value="5"
             aria-label="Battery voltage">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Resistance (R) <span class="ctrl-unit">Ω</span></span>
        <span class="val-badge" id="badge-resistance">10</span>
      </div>
      <input type="range" id="resistance" min="5" max="100" step="1" value="10"
             aria-label="Circuit resistance">
    </div>"""

    presets = """  <div class="presets">
    <button data-v="1.5" data-r="10">AA Battery</button>
    <button data-v="5"   data-r="10">USB 5V</button>
    <button data-v="12"  data-r="50">Car Battery</button>
    <button data-v="24"  data-r="100">High R</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var v = this.getAttribute('data-v'), r = this.getAttribute('data-r');
        function _set(id, val) {
          var el = document.getElementById(id); if (el) el.value = val;
          var bg = document.getElementById('badge-' + id); if (bg) bg.textContent = val;
        }
        _set('voltage', v); _set('resistance', r);
        window._state.set('voltage', parseFloat(v));
        window._state.set('resistance', parseFloat(r));
      });
    });
"""

    values = """    <div class="vcard"><div class="lbl">Current (A)</div><div class="num" id="val-current" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Power (W)</div><div class="num" id="val-power" style="color:#ec4899">0</div></div>
    <div class="vcard"><div class="lbl">Voltage (V)</div><div class="num" id="val-voltage" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">Resistance (Ω)</div><div class="num" id="val-resistance" style="color:#f59e0b">0</div></div>"""

    full_script = ELECTRICITY_ENGINE + "\n" + presets_script

    return build_simulation_html(
        spec,
        custom_script  = full_script,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment(spec),
        custom_presets = presets,
    )


def _build_waves(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Frequency (f) <span class="ctrl-unit">Hz</span></span>
        <span class="val-badge" id="badge-frequency">2.0</span>
      </div>
      <input type="range" id="frequency" min="0.5" max="10" step="0.1" value="2">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Amplitude (A) <span class="ctrl-unit">px</span></span>
        <span class="val-badge" id="badge-amplitude">50</span>
      </div>
      <input type="range" id="amplitude" min="5" max="120" step="1" value="50">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Wave Speed (v) <span class="ctrl-unit">px/s</span></span>
        <span class="val-badge" id="badge-speed">60</span>
      </div>
      <input type="range" id="speed" min="10" max="200" step="5" value="60">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Superposition <span class="ctrl-unit">(0→1)</span></span>
        <span class="val-badge" id="badge-superposition">0.0</span>
      </div>
      <input type="range" id="superposition" min="0" max="1" step="0.05" value="0">
    </div>"""

    values = """    <div class="vcard"><div class="lbl">Wavelength</div><div class="num" id="val-wavelength" style="color:#6366f1">—</div></div>
    <div class="vcard"><div class="lbl">Period (s)</div><div class="num" id="val-period" style="color:#10b981">—</div></div>"""

    return build_simulation_html(
        spec,
        custom_script  = WAVES_ENGINE,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment(spec),
    )


def _build_forces(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Applied Force (F) <span class="ctrl-unit">N</span></span>
        <span class="val-badge" id="badge-applied_force">20</span>
      </div>
      <input type="range" id="applied_force" min="-40" max="80" step="1" value="20">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Mass (m) <span class="ctrl-unit">kg</span></span>
        <span class="val-badge" id="badge-mass">5</span>
      </div>
      <input type="range" id="mass" min="0.5" max="20" step="0.5" value="5">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Friction (μ) <span class="ctrl-unit"></span></span>
        <span class="val-badge" id="badge-friction">0.20</span>
      </div>
      <input type="range" id="friction" min="0" max="1" step="0.02" value="0.2">
    </div>"""

    values = """    <div class="vcard"><div class="lbl">Net Force (N)</div><div class="num" id="val-net_force" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Accel (m/s²)</div><div class="num" id="val-acceleration" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">Velocity (m/s)</div><div class="num" id="val-velocity" style="color:#06b6d4">0</div></div>
    <div class="vcard"><div class="lbl">Friction (N)</div><div class="num" id="val-friction_force" style="color:#ef4444">0</div></div>"""

    return build_simulation_html(
        spec,
        custom_script  = FORCES_ENGINE,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment(spec),
    )


def _build_energy(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Mass (m) <span class="ctrl-unit">kg</span></span>
        <span class="val-badge" id="badge-mass">1.0</span>
      </div>
      <input type="range" id="mass" min="0.1" max="5" step="0.1" value="1">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Pendulum Length (L) <span class="ctrl-unit">m</span></span>
        <span class="val-badge" id="badge-length">1.0</span>
      </div>
      <input type="range" id="length" min="0.2" max="3" step="0.1" value="1">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Gravity (g) <span class="ctrl-unit">m/s²</span></span>
        <span class="val-badge" id="badge-gravity">9.81</span>
      </div>
      <input type="range" id="gravity" min="0.5" max="30" step="0.1" value="9.81">
    </div>"""

    presets = """  <div class="presets">
    <button data-g="9.81" data-l="1">Earth</button>
    <button data-g="1.62" data-l="1">Moon</button>
    <button data-g="3.72" data-l="1">Mars</button>
    <button data-g="24.8" data-l="1">Jupiter</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var g = this.getAttribute('data-g'), l = this.getAttribute('data-l');
        function _set(id, val) {
          var el = document.getElementById(id); if (el) el.value = val;
          var bg = document.getElementById('badge-' + id); if (bg) bg.textContent = val;
        }
        _set('gravity', g); _set('length', l);
        window._state.set('gravity', parseFloat(g));
        window._state.set('length',  parseFloat(l));
        var engine = window._engine;
        if (engine) { engine.omega = 0; }
      });
    });
"""

    values = """    <div class="vcard"><div class="lbl">Angle (°)</div><div class="num" id="val-theta" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Period (s)</div><div class="num" id="val-period" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">PE (J)</div><div class="num" id="val-pe" style="color:#f59e0b">0</div></div>
    <div class="vcard"><div class="lbl">KE (J)</div><div class="num" id="val-ke" style="color:#8b5cf6">0</div></div>"""

    full_script = ENERGY_ENGINE + "\n" + presets_script

    return build_simulation_html(
        spec,
        custom_script  = full_script,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment(spec),
        custom_presets = presets,
    )


def _build_buoyancy(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Mass (m) <span class="ctrl-unit">kg</span></span>
        <span class="val-badge" id="badge-mass">1.0</span>
      </div>
      <input type="range" id="mass" min="0.1" max="5" step="0.1" value="1">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Volume (V) <span class="ctrl-unit">L (×10⁻³ m³)</span></span>
        <span class="val-badge" id="badge-volume">0.0010</span>
      </div>
      <input type="range" id="volume" min="0.0002" max="0.004" step="0.0001" value="0.001">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Fluid Density (ρ_f) <span class="ctrl-unit">kg/m³</span></span>
        <span class="val-badge" id="badge-fluid_density">1000</span>
      </div>
      <input type="range" id="fluid_density" min="100" max="2000" step="10" value="1000">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Gravity (g) <span class="ctrl-unit">m/s²</span></span>
        <span class="val-badge" id="badge-gravity">9.81</span>
      </div>
      <input type="range" id="gravity" min="0.5" max="30" step="0.1" value="9.81">
    </div>"""

    presets = """  <div class="presets">
    <button data-mass="0.25" data-vol="0.003"  data-rho="1000" data-g="9.81">Cork (floats)</button>
    <button data-mass="1"    data-vol="0.001"  data-rho="1000" data-g="9.81">Neutral</button>
    <button data-mass="3"    data-vol="0.0005" data-rho="1000" data-g="9.81">Rock (sinks)</button>
    <button data-mass="1"    data-vol="0.001"  data-rho="1260" data-g="9.81">Salt Water</button>
    <button data-mass="1"    data-vol="0.001"  data-rho="1000" data-g="1.62">Moon</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var mass = this.getAttribute('data-mass'), vol = this.getAttribute('data-vol');
        var rho  = this.getAttribute('data-rho'),  g   = this.getAttribute('data-g');
        function _set(id, val, prec) {
          var el = document.getElementById(id); if (el) el.value = val;
          var bg = document.getElementById('badge-' + id);
          if (bg) bg.textContent = prec ? parseFloat(val).toFixed(prec) : val;
        }
        _set('mass', mass, 1); _set('volume', vol, 4);
        _set('fluid_density', rho, 0); _set('gravity', g, 2);
        window._state.set('mass',          parseFloat(mass));
        window._state.set('volume',        parseFloat(vol));
        window._state.set('fluid_density', parseFloat(rho));
        window._state.set('gravity',       parseFloat(g));
        var engine = window._engine;
        if (engine) { engine.blockVy = 0; engine.blockY = 0; engine.settled = false; }
      });
    });
"""

    values = """    <div class="vcard"><div class="lbl">Weight (N)</div><div class="num" id="val-weight" style="color:#ef4444">0</div></div>
    <div class="vcard"><div class="lbl">Buoyancy (N)</div><div class="num" id="val-buoyant_force" style="color:#0ea5e9">0</div></div>
    <div class="vcard"><div class="lbl">Net Force (N)</div><div class="num" id="val-net_force" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">ρ ratio</div><div class="num" id="val-density_ratio" style="color:#f59e0b">0</div></div>
    <div class="vcard"><div class="lbl">Sub. Frac.</div><div class="num" id="val-submerged_fraction" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">Obj ρ (kg/m³)</div><div class="num" id="val-object_density" style="color:#06b6d4">0</div></div>"""

    full_script = BUOYANCY_ENGINE + "\n" + presets_script

    return build_simulation_html(
        spec,
        custom_script  = full_script,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment(spec),
        custom_presets = presets,
    )


def _build_assessment(spec: SimulationSpecification) -> str:
    return _build_assessment_html(spec)