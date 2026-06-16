from __future__ import annotations

from app.simulation_engine.schemas import SimulationSpecification
from app.simulation_engine.templates.base_template import build_simulation_html


DIFFUSION_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.particles = [];
    this.membraneX = 0;
    this.leftCount = 0;
    this.rightCount = 0;
  }
  resetParticles(count) {
    this.particles = [];
    for (let i = 0; i < count; i++) {
      this.particles.push({
        x: 30 + Math.random() * (this.canvas.width - 60),
        y: 30 + Math.random() * (this.canvas.height - 100),
        vx: (Math.random() - 0.5) * 80,
        vy: (Math.random() - 0.5) * 80,
        size: 3 + Math.random() * 4,
      });
    }
    this.updateCounts();
  }
  updateCounts() {
    const mx = this.canvas.width / 2;
    this.leftCount = this.particles.filter(function(p) { return p.x < mx; }).length;
    this.rightCount = this.particles.filter(function(p) { return p.x >= mx; }).length;
  }
  update(dt, state) {
    const temp = state.get('temperature') || 300;
    const conc = state.get('concentration') || 50;
    const particleSize = state.get('particle_size') || 5;

    if (this.particles.length === 0) {
      const totalParticles = Math.round(conc * 0.5);
      for (let i = 0; i < totalParticles; i++) {
        this.particles.push({
          x: 20 + (i < totalParticles * 0.7 ? (Math.random() * this.canvas.width * 0.45) : (this.canvas.width * 0.55 + Math.random() * this.canvas.width * 0.35)),
          y: 30 + Math.random() * (this.canvas.height - 100),
          vx: (Math.random() - 0.5) * 80,
          vy: (Math.random() - 0.5) * 80,
          size: 3 + (particleSize / 10) * 4,
        });
      }
      this.updateCounts();
    }

    const speed = (temp / 300) * (5 / particleSize || 1);
    this.particles.forEach(function(p) {
      p.x += p.vx * dt * speed;
      p.y += p.vy * dt * speed;
      if (p.x < 5) p.x = 5;
      if (p.x > this.canvas.width - 5) p.x = this.canvas.width - 5;
      if (p.y < 30) p.y = 30;
      if (p.y > this.canvas.height - 30) p.y = this.canvas.height - 30;
    }, this);

    this.updateCounts();
    state.set('left_count', this.leftCount);
    state.set('right_count', this.rightCount);
    state.set('total_flux', Math.abs(this.leftCount - this.rightCount));
    const avgDist = this.particles.reduce(function(s, p) {
      const mx = this.canvas.width / 2;
      return s + Math.abs(p.x - mx);
    }.bind(this), 0) / (this.particles.length || 1);
    state.set('avg_distance', avgDist.toFixed(0));
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

    const mx = w / 2;
    ctx.strokeStyle = '#8b5cf6';
    ctx.lineWidth = 3;
    ctx.setLineDash([8, 6]);
    ctx.beginPath();
    ctx.moveTo(mx, 30);
    ctx.lineTo(mx, h - 30);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = '#8b5cf6';
    ctx.font = 'bold 10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('MEMBRANE', mx, 18);
    ctx.textAlign = 'left';

    const engine = window._engine;
    if (engine) {
      engine.particles.forEach(function(p) {
        ctx.fillStyle = p.x < mx ? '#3b82f6' : '#f43f5e';
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('Left: ' + (state.get('left_count') || 0) + ' particles', 10, 20);
    ctx.fillStyle = '#475569';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Right: ' + (state.get('right_count') || 0) + ' particles', w - 160, 20);
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
        if (window._engine) window._engine.particles = [];
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

POPULATION_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.time = 0;
    this.popHistory = [];
  }
  update(dt, state) {
    this.time += dt;
    const birthRate = state.get('birth_rate') || 0.5;
    const deathRate = state.get('death_rate') || 0.3;
    const carrying = state.get('carrying_capacity') || 500;
    let pop = state.get('population') || 10;

    const r = birthRate - deathRate;
    const logisticGrowth = r * pop * (1 - pop / carrying);
    pop += logisticGrowth * dt * 10;
    if (pop < 0) pop = 0;
    pop = Math.round(pop * 10) / 10;

    state.set('population', pop);
    state.set('growth_rate', logisticGrowth);
    state.set('births', birthRate * pop * dt * 10);
    state.set('deaths', deathRate * pop * dt * 10);

    this.popHistory.push({ t: this.time, pop: pop });
    if (this.popHistory.length > 400) this.popHistory.shift();
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

    const pop = state.get('population') || 0;
    const cap = state.get('carrying_capacity') || 500;

    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(20, h - 80, w - 40, 50);

    const barW = (w - 60) * (Math.min(pop, cap) / cap);
    ctx.fillStyle = '#22c55e';
    ctx.fillRect(30, h - 70, barW, 30);

    ctx.strokeStyle = '#ef4444';
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1.5;
    const capX = 30 + (w - 60);
    ctx.beginPath(); ctx.moveTo(capX, h - 80); ctx.lineTo(capX, h - 30); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#ef4444';
    ctx.font = 'bold 9px sans-serif';
    ctx.fillText('K=' + cap.toFixed(0), capX - 15, h - 84);

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('Population: ' + pop.toFixed(0), 10, 20);
    ctx.fillStyle = '#475569';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Growth Rate: ' + (state.get('growth_rate') || 0).toFixed(3), 10, 36);

    const dotCount = Math.min(Math.round(pop / 5), 200);
    for (let i = 0; i < dotCount; i++) {
      ctx.fillStyle = '#22c55e';
      ctx.globalAlpha = 0.5;
      const dx = 40 + Math.random() * (w - 80);
      const dy = 60 + Math.random() * (h - 170);
      ctx.beginPath();
      ctx.arc(dx, dy, 2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
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


def build_biology_simulation(spec: SimulationSpecification) -> str:
    sim_type = spec.simulation_type.value

    if sim_type == "diffusion":
        return build_simulation_html(spec, custom_script=DIFFUSION_ENGINE)
    elif sim_type == "population_growth":
        return build_simulation_html(spec, custom_script=POPULATION_ENGINE)
    elif sim_type == "membrane_transport":
        return build_simulation_html(spec, custom_script=_membrane_transport_script())
    else:
        return build_simulation_html(spec, custom_script=_generic_biology_script())


def _membrane_transport_script() -> str:
    return """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.particles = [];
    this.proteins = [];
    this.time = 0;
    for (let i = 0; i < 30; i++) {
      const side = Math.random() < 0.6 ? 'out' : 'in';
      this.particles.push({
        x: side === 'out' ? 10 + Math.random() * 100 : canvas.width - 110 + Math.random() * 100,
        y: 40 + Math.random() * (canvas.height - 80),
        vx: (Math.random() - 0.5) * 40, vy: (Math.random() - 0.5) * 40,
        side: side, transported: false,
      });
    }
    for (let i = 0; i < 3; i++) {
      this.proteins.push({ y: 80 + i * 100, active: true });
    }
    this.transportedCount = 0;
  }
  update(dt, state) {
    this.time += dt;
    const gradient = state.get('concentration_gradient') || 50;
    const atp = state.get('atp_available') || 50;
    const mx = this.canvas.width / 2;

    this.particles.forEach(function(p) {
      p.x += p.vx * dt; p.y += p.vy * dt;
      if (p.y < 40 || p.y > this.canvas.height - 40) p.vy *= -1;

      if (!p.transported && Math.abs(p.x - mx) < 5 && atp > 0) {
        if (p.side === 'out' && Math.random() < gradient * 0.002) {
          p.side = 'in';
          p.transported = true;
          this.transportedCount++;
        }
      }
      if (p.x < 5) p.x = 5;
      if (p.x > this.canvas.width - 5) p.x = this.canvas.width - 5;
    }, this);

    state.set('transported', this.transportedCount);
    state.set('atp_used', Math.min(this.transportedCount, Math.round(atp)));
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
    const mx = w / 2;

    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(0, 30, mx - 15, h - 60);

    ctx.fillStyle = '#f1f5f9';
    ctx.fillRect(mx + 15, 30, w - mx - 15, h - 60);

    ctx.fillStyle = '#8b5cf6';
    ctx.fillRect(mx - 15, 30, 30, h - 60);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 9px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('MEMBRANE', mx, 15);

    const engine = window._engine;
    if (engine) {
      engine.proteins.forEach(function(p) {
        ctx.fillStyle = '#f59e0b';
        ctx.fillRect(mx - 22, p.y - 8, 44, 16);
        ctx.fillStyle = '#1e293b';
        ctx.font = 'bold 7px sans-serif';
        ctx.fillText('Protein', mx, p.y + 3);
      });
    }

    if (engine) {
      engine.particles.forEach(function(p) {
        ctx.fillStyle = p.side === 'out' ? '#3b82f6' : '#22c55e';
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fill();
        if (p.transported) {
          ctx.strokeStyle = '#f59e0b';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(p.x, p.y, 7, 0, Math.PI * 2);
          ctx.stroke();
        }
      });
    }
    ctx.textAlign = 'left';

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText('Extracellular', 10, 45);
    ctx.fillText('Intracellular', w - 100, 45);
    ctx.fillStyle = '#475569';
    ctx.font = '10px sans-serif';
    ctx.fillText('Transported: ' + (state.get('transported') || 0), 10, h - 10);
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


def _generic_biology_script() -> str:
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
    ctx.textAlign = 'center'; ctx.fillText('Biology Simulation Ready', w/2, h/2 - 10); ctx.textAlign = 'left';
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
