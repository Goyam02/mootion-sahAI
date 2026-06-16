from __future__ import annotations

from app.simulation_engine.schemas import SimulationSpecification
from app.simulation_engine.templates.base_template import build_simulation_html


FUNCTIONS_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
  }
  update(dt, state) {
    const a = state.get('a') || 1;
    const b = state.get('b') || 0;
    const c = state.get('c') || 0;
    const w = this.canvas.width, h = this.canvas.height;
    const points = [];
    for (let px = 0; px <= w; px++) {
      const x = (px / w) * 8 - 4;
      const y = a * x * x + b * x + c;
      points.push({ x: px, y: -y * 20 + h / 2 });
    }
    state.set('function_points', points);
    const discriminant = b * b - 4 * a * c;
    state.set('discriminant', discriminant);
    if (discriminant >= 0) {
      const root1 = (-b + Math.sqrt(discriminant)) / (2 * a);
      const root2 = (-b - Math.sqrt(discriminant)) / (2 * a);
      state.set('roots', root1.toFixed(2) + ', ' + root2.toFixed(2));
    } else {
      state.set('roots', 'No real roots');
    }
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

    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 25) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 25) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2); ctx.stroke();

    const points = state.get('function_points') || [];
    if (points.length > 1) {
      ctx.strokeStyle = '#8b5cf6';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      let started = false;
      points.forEach(function(p) {
        if (p.y > -1000 && p.y < h + 1000) {
          if (!started) { ctx.moveTo(p.x, p.y); started = true; }
          else ctx.lineTo(p.x, p.y);
        } else {
          started = false;
        }
      });
      ctx.stroke();
    }

    const a = state.get('a') || 1;
    const b = state.get('b') || 0;
    const c = state.get('c') || 0;
    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('f(x) = ' + a.toFixed(1) + 'x^2 + ' + b.toFixed(1) + 'x + ' + c.toFixed(1), 10, 20);
    ctx.fillStyle = '#475569';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Discriminant: ' + (state.get('discriminant') || 0).toFixed(2), 10, 36);
    ctx.fillStyle = '#6366f1';
    ctx.fillText('Roots: ' + (state.get('roots') || ''), 10, 52);
  }
}

class ControlsManager {
  constructor(state, bus) { this.state = state; this.bus = bus; this.sliders = []; }
  bind() {
    var self = this;
    document.querySelectorAll('input[type="range"]').forEach(function(input) {
      if (input.id === 'speed-slider') return;
      var key = input.id;
      self.sliders.push(input);
      self.state.set(key, parseFloat(input.value));
      input.addEventListener('input', function() {
        var val = parseFloat(this.value);
        self.state.set(key, val);
        var badge = document.getElementById('badge-' + key);
        if (badge) badge.textContent = val.toFixed(1);
      });
    });
  }
  sync() {
    this.sliders.forEach(function(input) {
      var val = this.state.get(input.id);
      if (val !== undefined) input.value = val;
    }, this);
  }
  syncLabels() {
    var all = this.state.getAll();
    this.sliders.forEach(function(input) {
      var val = all[input.id];
      if (val !== undefined) {
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

PROBABILITY_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.results = [];
    this.coinFlips = [];
    this.totalFlips = 0;
    this.heads = 0;
  }
  update(dt, state) {
    const trials = state.get('trials') || 10;
    const prob = state.get('probability') || 0.5;

    if (this.totalFlips < trials) {
      for (let i = 0; i < 3 && this.totalFlips < trials; i++) {
        const result = Math.random() < prob ? 'H' : 'T';
        this.coinFlips.push(result);
        if (result === 'H') this.heads++;
        this.totalFlips++;
      }
    }

    state.set('total_flips', this.totalFlips);
    state.set('heads', this.heads);
    state.set('tails', this.totalFlips - this.heads);
    state.set('heads_pct', this.totalFlips > 0 ? (this.heads / this.totalFlips) * 100 : 0);
    state.set('tails_pct', this.totalFlips > 0 ? ((this.totalFlips - this.heads) / this.totalFlips) * 100 : 0);
    state.set('expected_heads', prob * 100);
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

    const heads = state.get('heads') || 0;
    const tails = state.get('tails') || 0;
    const total = state.get('total_flips') || 0;

    const barW = 120, barH = 20;
    const barX = w / 2 - barW / 2, barY = h / 2 - 20;

    if (total > 0) {
      const hFrac = heads / total;
      ctx.fillStyle = '#e2e8f0';
      ctx.fillRect(barX, barY, barW, barH);
      ctx.fillStyle = '#22c55e';
      ctx.fillRect(barX, barY, barW * hFrac, barH);
      ctx.fillStyle = '#3b82f6';
      ctx.fillRect(barX + barW * hFrac, barY, barW * (1 - hFrac), barH);

      ctx.fillStyle = '#1e293b';
      ctx.font = 'bold 11px sans-serif';
      ctx.fillText('Heads: ' + heads + ' (' + (state.get('heads_pct') || 0).toFixed(1) + '%)', barX, barY - 8);
      ctx.fillStyle = '#475569';
      ctx.font = '10px sans-serif';
      ctx.fillText('Tails: ' + tails + ' (' + (state.get('tails_pct') || 0).toFixed(1) + '%)', barX, barY + barH + 18);

      const expectedX = barX + barW * (state.get('expected_heads') || 50) / 100;
      ctx.strokeStyle = '#f59e0b';
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(expectedX, barY - 5); ctx.lineTo(expectedX, barY + barH + 5);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#f59e0b';
      ctx.font = 'bold 9px sans-serif';
      ctx.fillText('Expected: ' + (state.get('expected_heads') || 0).toFixed(0) + '%', expectedX - 30, barY + barH + 35);

      const engine = window._engine;
      if (engine) {
        const recent = engine.coinFlips.slice(-20);
        ctx.fillStyle = '#64748b';
        ctx.font = '14px "Courier New", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(recent.join(' '), w / 2, h - 40);
        ctx.textAlign = 'left';
      }
    } else {
      ctx.fillStyle = '#64748b';
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Click RESET to start coin flips', w / 2, h / 2);
      ctx.textAlign = 'left';
    }

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('Total Flips: ' + total, 10, 20);
  }
}

class ControlsManager {
  constructor(state, bus) { this.state = state; this.bus = bus; this.sliders = []; }
  bind() {
    var self = this;
    document.querySelectorAll('input[type="range"]').forEach(function(input) {
      if (input.id === 'speed-slider') return;
      var key = input.id;
      self.sliders.push(input);
      self.state.set(key, parseFloat(input.value));
      input.addEventListener('input', function() {
        var val = parseFloat(this.value);
        self.state.set(key, val);
        var badge = document.getElementById('badge-' + key);
        if (badge) badge.textContent = val.toFixed(2);
      });
    });
  }
  sync() {
    this.sliders.forEach(function(input) {
      var val = this.state.get(input.id);
      if (val !== undefined) input.value = val;
    }, this);
  }
  syncLabels() {
    var all = this.state.getAll();
    this.sliders.forEach(function(input) {
      var val = all[input.id];
      if (val !== undefined) {
        var badge = document.getElementById('badge-' + input.id);
        if (badge) badge.textContent = typeof val === 'number' ? val.toFixed(2) : val;
      }
    });
  }
}

class AssessmentEngine {
  constructor(state, bus) { this.state = state; this.bus = bus; }
  getCurrentQuestion() { return document.getElementById('assess-q')?.textContent || ''; }
}
"""


def build_math_simulation(spec: SimulationSpecification) -> str:
    sim_type = spec.simulation_type.value

    if sim_type == "functions":
        return build_simulation_html(spec, custom_script=FUNCTIONS_ENGINE)
    elif sim_type == "probability":
        return build_simulation_html(spec, custom_script=PROBABILITY_ENGINE)
    elif sim_type == "statistics":
        return build_simulation_html(spec, custom_script=_statistics_script())
    elif sim_type == "geometry":
        return build_simulation_html(spec, custom_script=_geometry_script())
    else:
        return build_simulation_html(spec, custom_script=_generic_math_script())


def _statistics_script() -> str:
    return """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.data = [];
    this.time = 0;
  }
  update(dt, state) {
    this.time += dt;
    const sampleSize = Math.round(state.get('sample_size') || 30);
    const mean = state.get('mean') || 50;
    const std = state.get('std_dev') || 10;
    const bins = 20;
    while (this.data.length < sampleSize) {
      const x = mean + std * (Math.random() + Math.random() + Math.random() + Math.random() + Math.random() + Math.random() - 3);
      this.data.push(Math.round(x * 10) / 10);
    }
    if (this.data.length > sampleSize) this.data = this.data.slice(0, sampleSize);
    this.data.sort(function(a, b) { return a - b; });
    const sum = this.data.reduce(function(s, v) { return s + v; }, 0);
    const n = this.data.length;
    const actualMean = sum / n;
    const variance = this.data.reduce(function(s, v) { return s + (v - actualMean) ** 2; }, 0) / n;
    state.set('actual_mean', actualMean.toFixed(2));
    state.set('actual_std', Math.sqrt(variance).toFixed(2));
    state.set('median', (this.data.length % 2 === 0 ? (this.data[n/2 - 1] + this.data[n/2]) / 2 : this.data[Math.floor(n/2)]).toFixed(2));
    state.set('data_points', this.data);
    state.set('bins', bins);
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
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 25) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 25) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    const data = state.get('data_points') || [];
    const bins = state.get('bins') || 20;
    if (data.length > 0) {
      const min = data[0], max = data[data.length - 1];
      const range = max - min || 1;
      const binW = (w - 60) / bins;
      const histogram = new Array(bins).fill(0);
      data.forEach(function(v) {
        const idx = Math.min(bins - 1, Math.floor(((v - min) / range) * bins));
        histogram[idx]++;
      });
      const maxCount = Math.max.apply(null, histogram) || 1;
      const barH = h - 80;
      histogram.forEach(function(count, i) {
        const bh = (count / maxCount) * barH;
        ctx.fillStyle = '#6366f1';
        ctx.fillRect(30 + i * binW, h - 40 - bh, binW - 1, bh);
      });
    }

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('Mean: ' + (state.get('actual_mean') || ''), 10, 20);
    ctx.fillStyle = '#475569';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Std Dev: ' + (state.get('actual_std') || ''), 10, 36);
    ctx.fillStyle = '#6366f1';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Median: ' + (state.get('median') || ''), 10, 52);
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


def _geometry_script() -> str:
    return """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
  }
  update(dt, state) {
    const sides = Math.round(state.get('sides') || 3);
    const radius = state.get('radius') || 80;
    const cx = this.canvas.width / 2, cy = this.canvas.height / 2;
    const verts = [];
    for (let i = 0; i < sides; i++) {
      const a = (i / sides) * Math.PI * 2 - Math.PI / 2;
      verts.push({ x: cx + radius * Math.cos(a), y: cy + radius * Math.sin(a) });
    }
    state.set('vertices', verts);
    state.set('sides', sides);
    const area = 0.5 * sides * radius * radius * Math.sin(2 * Math.PI / sides);
    const perimeter = 2 * sides * radius * Math.sin(Math.PI / sides);
    state.set('area', area.toFixed(1));
    state.set('perimeter', perimeter.toFixed(1));
    const intAngle = (sides - 2) * 180 / sides;
    state.set('interior_angle', intAngle.toFixed(1));
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

    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 25) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 25) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    const verts = state.get('vertices') || [];
    if (verts.length > 2) {
      ctx.strokeStyle = '#6366f1';
      ctx.lineWidth = 2.5;
      ctx.fillStyle = 'rgba(99, 102, 241, 0.08)';
      ctx.beginPath();
      verts.forEach(function(v, i) { if (i === 0) ctx.moveTo(v.x, v.y); else ctx.lineTo(v.x, v.y); });
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      verts.forEach(function(v, i) {
        ctx.fillStyle = '#6366f1';
        ctx.beginPath();
        ctx.arc(v.x, v.y, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#1e293b';
        ctx.font = '10px sans-serif';
        ctx.fillText('V' + (i + 1), v.x + 8, v.y + 4);
      });
    }

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('Sides: ' + (state.get('sides') || 3), 10, 20);
    ctx.fillStyle = '#475569';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Area: ' + (state.get('area') || ''), 10, 36);
    ctx.fillStyle = '#6366f1';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Perimeter: ' + (state.get('perimeter') || ''), 10, 52);
    ctx.fillText('Int. Angle: ' + (state.get('interior_angle') || '') + '\\u00b0', 10, 68);
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


def _generic_math_script() -> str:
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
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 25) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 25) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 14px sans-serif';
    ctx.textAlign = 'center'; ctx.fillText('Math Simulation Ready', w/2, h/2 - 10); ctx.textAlign = 'left';
    ctx.fillStyle = '#64748b'; ctx.font = '12px sans-serif';
    ctx.textAlign = 'center'; ctx.fillText('Adjust controls and press Play', w/2, h/2 + 12); ctx.textAlign = 'left';
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
