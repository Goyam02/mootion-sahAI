from __future__ import annotations

from app.simulation_engine.schemas import SimulationSpecification
from app.simulation_engine.templates.base_template import build_simulation_html


ATOMIC_STRUCTURE_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.angle = 0;
    this.electrons = [];
    for (let i = 0; i < 8; i++) {
      const shell = i < 2 ? 0 : (i < 4 ? 1 : 2);
      this.electrons.push({
        angle: (i * 2.3999) % (Math.PI * 2),
        radius: 60 + shell * 35,
        shell: shell,
      });
    }
  }
  update(dt, state) {
    this.angle += dt * 0.8;
    const protons = Math.round(state.get('protons') || 6);
    const neutrons = Math.round(state.get('neutrons') || 6);
    state.set('atomic_number', protons);
    state.set('mass_number', protons + neutrons);
    const maxShell = Math.min(3, Math.ceil((protons - 2) / 8) + 1);
    state.set('shells', maxShell);
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

    const cx = w / 2, cy = h / 2;
    const engine = window._engine;

    for (let r = 60; r <= 130; r += 35) {
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
    }

    if (engine) {
      engine.electrons.forEach(function(e) {
        const ex = cx + e.radius * Math.cos(e.angle + engine.angle / (1 + e.shell * 0.5));
        const ey = cy + e.radius * Math.sin(e.angle + engine.angle / (1 + e.shell * 0.5));
        ctx.beginPath();
        ctx.arc(ex, ey, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#06b6d4';
        ctx.fill();
      });
    }

    const protons = state.get('protons') || 6;
    const neutrons = state.get('neutrons') || 6;

    ctx.fillStyle = '#ef4444';
    for (let i = 0; i < Math.min(protons, 20); i++) {
      const a = (i * 2.4) % (Math.PI * 2);
      const rn = 6 + Math.random() * 8;
      const nx = cx + rn * Math.cos(a);
      const ny = cy + rn * Math.sin(a);
      ctx.beginPath();
      ctx.arc(nx, ny, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.fillStyle = '#8b5cf6';
    for (let i = 0; i < Math.min(neutrons, 20); i++) {
      const a = (i * 2.1 + 1) % (Math.PI * 2);
      const rn = 6 + Math.random() * 8;
      const nx = cx + rn * Math.cos(a);
      const ny = cy + rn * Math.sin(a);
      ctx.beginPath();
      ctx.arc(nx, ny, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('Protons: ' + protons + '  Neutrons: ' + neutrons, 10, 20);
    ctx.fillStyle = '#475569';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Atomic #: ' + (state.get('atomic_number') || 6) + '  Mass #: ' + (state.get('mass_number') || 12), 10, 36);
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
        if (badge) badge.textContent = val.toFixed(0);
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


MOLECULAR_POLARITY_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.atoms = [];
    this.dipoleAngle = 0;
  }
  update(dt, state) {
    const en1 = state.get('electronegativity_1') || 2.1;
    const en2 = state.get('electronegativity_2') || 3.5;
    const diff = Math.abs(en1 - en2);

    state.set('en_difference', diff);
    state.set('bond_polarity', diff > 0.4 ? 'Polar' : 'Non-polar');
    state.set('bond_strength', diff > 1.7 ? 'Ionic' : (diff > 0.4 ? 'Polar Covalent' : 'Non-polar Covalent'));

    this.dipoleAngle += dt * 0.5;
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

    const cx = w / 2, cy = h / 2;
    const en1 = state.get('electronegativity_1') || 2.1;
    const en2 = state.get('electronegativity_2') || 3.5;
    const diff = Math.abs(en1 - en2);

    const r1 = 35 + en1 * 5;
    const r2 = 35 + en2 * 5;

    ctx.fillStyle = en1 > en2 ? '#ef4444' : '#3b82f6';
    ctx.beginPath();
    ctx.arc(cx - 50, cy, r1, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = en2 > en1 ? '#ef4444' : '#3b82f6';
    ctx.beginPath();
    ctx.arc(cx + 50, cy, r2, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('EN: ' + en1.toFixed(1), cx - 50, cy + r1 + 18);
    ctx.fillText('EN: ' + en2.toFixed(1), cx + 50, cy + r2 + 18);
    ctx.textAlign = 'left';

    const bondW = 80;
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(cx - 50 + r1 * 0.7, cy);
    ctx.lineTo(cx + 50 - r2 * 0.7, cy);
    ctx.stroke();

    if (diff > 0.4) {
      const dir = en2 > en1 ? 1 : -1;
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 2;
      const arrowX = cx + dir * 30;
      ctx.beginPath();
      ctx.moveTo(cx - dir * 20, cy - 30);
      ctx.lineTo(arrowX, cy - 30);
      ctx.lineTo(arrowX - dir * 8, cy - 36);
      ctx.moveTo(arrowX, cy - 30);
      ctx.lineTo(arrowX - dir * 8, cy - 24);
      ctx.stroke();
      ctx.fillStyle = '#f59e0b';
      ctx.font = '10px sans-serif';
      ctx.fillText('Dipole ' + (dir > 0 ? '->' : '<-'), cx - 15, cy - 38);
    }

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('EN Difference: ' + diff.toFixed(2), 10, 20);
    ctx.fillStyle = '#475569';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Bond Type: ' + (state.get('bond_strength') || ''), 10, 36);
    ctx.fillStyle = '#6366f1';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Polarity: ' + (state.get('bond_polarity') || ''), 10, 52);

    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(w - 160, h - 40, 140, 20);
    const grad = ctx.createLinearGradient(w - 160, 0, w - 20, 0);
    grad.addColorStop(0, '#3b82f6');
    grad.addColorStop(0.5, '#8b5cf6');
    grad.addColorStop(1, '#ef4444');
    ctx.fillStyle = grad;
    ctx.fillRect(w - 160, h - 40, 140, 20);
    ctx.fillStyle = '#64748b';
    ctx.font = '8px sans-serif';
    ctx.fillText('Low EN', w - 155, h - 44);
    ctx.fillText('High EN', w - 55, h - 44);
    const markX = w - 160 + (en1 / 4.0) * 140;
    ctx.fillStyle = '#1e293b';
    ctx.beginPath();
    ctx.arc(markX, h - 30, 4, 0, Math.PI * 2);
    ctx.fill();
    const markX2 = w - 160 + (en2 / 4.0) * 140;
    ctx.beginPath();
    ctx.arc(markX2, h - 30, 4, 0, Math.PI * 2);
    ctx.fill();
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


REACTIONS_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.molecules = [];
    this.products = [];
    this.reactionProgress = 0;
    this.isReacting = false;
    this.reactionComplete = false;
    for (let i = 0; i < 12; i++) {
      this.molecules.push({
        x: Math.random() * 250 + 20, y: 60 + Math.random() * 200,
        vx: (Math.random() - 0.5) * 60, vy: (Math.random() - 0.5) * 60,
        type: i < 6 ? 'A' : 'B', size: 12 + Math.random() * 6,
      });
    }
  }
  update(dt, state) {
    const temp = state.get('temperature') || 300;
    const conc = state.get('concentration') || 50;

    const speed = (temp / 300) * (conc / 50);
    let collisionCount = 0;

    this.molecules.forEach(function(m) {
      m.x += m.vx * dt * speed;
      m.y += m.vy * dt * speed;
      if (m.x < 10 || m.x > 270) m.vx *= -1;
      if (m.y < 50 || m.y > 260) m.vy *= -1;
    });

    for (let i = 0; i < this.molecules.length; i++) {
      for (let j = i + 1; j < this.molecules.length; j++) {
        const a = this.molecules[i], b = this.molecules[j];
        if (a.type === b.type) continue;
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < a.size + b.size && temp > 200) {
          collisionCount++;
          a.vx = (Math.random() - 0.5) * 60;
          a.vy = (Math.random() - 0.5) * 60;
          b.vx = (Math.random() - 0.5) * 60;
          b.vy = (Math.random() - 0.5) * 60;
        }
      }
    }

    state.set('collision_rate', collisionCount);
    state.set('reaction_rate', collisionCount * 0.1);
    state.set('molecules_left', this.molecules.length);
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
    for (let x = 0; x < w; x += 30) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 30) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    const engine = window._engine;
    if (engine) {
      engine.molecules.forEach(function(m) {
        ctx.fillStyle = m.type === 'A' ? '#3b82f6' : '#ef4444';
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 9px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(m.type, m.x, m.y + 3);
        ctx.textAlign = 'left';
      });
    }

    ctx.fillStyle = '#1e293b';
    ctx.font = 'bold 11px "Courier New", monospace';
    ctx.fillText('Temperature: ' + (state.get('temperature') || 300).toFixed(0) + ' K', 10, 20);
    ctx.fillStyle = '#475569';
    ctx.font = '11px "Courier New", monospace';
    ctx.fillText('Reaction Rate: ' + (state.get('reaction_rate') || 0).toFixed(2), 10, 36);
    ctx.fillStyle = '#6366f1';
    ctx.fillText('Collisions/s: ' + (state.get('collision_rate') || 0).toFixed(0), 10, 52);
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


def build_chemistry_simulation(spec: SimulationSpecification) -> str:
    sim_type = spec.simulation_type.value

    if sim_type == "atomic_structure":
        return build_simulation_html(spec, custom_script=ATOMIC_STRUCTURE_ENGINE)
    elif sim_type == "molecular_polarity":
        return build_simulation_html(spec, custom_script=MOLECULAR_POLARITY_ENGINE)
    elif sim_type == "reactions":
        return build_simulation_html(spec, custom_script=REACTIONS_ENGINE)
    else:
        return build_simulation_html(spec, custom_script=_generic_chemistry_script())


def _generic_chemistry_script() -> str:
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
    ctx.textAlign = 'center'; ctx.fillText('Chemistry Simulation Ready', w/2, h/2 - 10); ctx.textAlign = 'left';
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
