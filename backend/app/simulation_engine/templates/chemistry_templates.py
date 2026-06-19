from __future__ import annotations

from app.simulation_engine.schemas import SimulationSpecification
from app.simulation_engine.templates.base_template import (
    build_simulation_html,
    build_custom_llm_simulation,
    _build_assessment_html,
)


# ════════════════════════════════════════════════════════════════════════════
# ATOMIC STRUCTURE
# Fixed: nucleus particles used Math.random() every draw frame → jitter.
# Now nucleus particle positions are pre-computed and stable.
# ════════════════════════════════════════════════════════════════════════════

ATOMIC_STRUCTURE_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.angle   = 0;
    // Pre-generate stable nucleus particle offsets (no random in draw!)
    this._nucleusProtonPos  = this._genNucleus(20, 4, 0);
    this._nucleusNeutronPos = this._genNucleus(20, 4, 1);
    // Electrons: up to 3 shells, positions computed from proton count
    this.electrons = this._buildElectrons(6);
    this._lastProtons = 6;
  }

  _genNucleus(count, radius, offset) {
    var pts = [];
    for (var i = 0; i < count; i++) {
      var a = (i / count) * Math.PI * 2 + offset * 0.9;
      var r = radius * (0.3 + 0.7 * ((i * 7919) % 100) / 100);
      pts.push({ dx: r * Math.cos(a), dy: r * Math.sin(a) });
    }
    return pts;
  }

  _buildElectrons(protons) {
    // Shell capacities: 2, 8, 18
    var shells = [2, 8, 18];
    var radii  = [65, 105, 148];
    var result = [];
    var remaining = protons;
    for (var s = 0; s < shells.length && remaining > 0; s++) {
      var count = Math.min(shells[s], remaining);
      for (var i = 0; i < count; i++) {
        result.push({
          angle:  (i / count) * Math.PI * 2,
          radius: radii[s],
          shell:  s,
          speed:  1.0 - s * 0.28,
        });
      }
      remaining -= count;
    }
    return result;
  }

  update(dt, state) {
    this.angle += dt * 0.9;
    const protons  = Math.max(1, Math.min(18, Math.round(state.get('protons')  || 6)));
    const neutrons = Math.max(0, Math.round(state.get('neutrons') || 6));

    if (protons !== this._lastProtons) {
      this.electrons     = this._buildElectrons(protons);
      this._lastProtons  = protons;
    }

    state.set('atomic_number', protons);
    state.set('mass_number',   protons + neutrons);

    // Determine shell count
    let shells = 0, remaining = protons;
    const caps = [2, 8, 18];
    for (let s = 0; s < caps.length && remaining > 0; s++) { shells++; remaining -= caps[s]; }
    state.set('shells', shells);

    // Element name lookup (H-Ar)
    const elements = [
      '', 'Hydrogen','Helium','Lithium','Beryllium','Boron','Carbon','Nitrogen',
      'Oxygen','Fluorine','Neon','Sodium','Magnesium','Aluminium','Silicon',
      'Phosphorus','Sulfur','Chlorine','Argon'
    ];
    state.set('element', elements[protons] || 'Unknown');
  }

  onReset() { this.angle = 0; }
  getHint()  { return 'Adjust protons to change the element; neutrons change the isotope'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Space-like background
    const bg = ctx.createRadialGradient(w/2, h/2, 10, w/2, h/2, Math.max(w, h) * 0.6);
    bg.addColorStop(0, '#1e1b4b'); bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);

    const cx = w / 2, cy = h / 2;
    const engine = window._engine;
    if (!engine) return;

    const protons  = state.get('protons')  || 6;
    const neutrons = state.get('neutrons') || 6;

    // Shell rings
    const radii = [65, 105, 148];
    const shells = state.get('shells') || 1;
    for (let s = 0; s < shells; s++) {
      ctx.strokeStyle = 'rgba(148,163,184,0.2)'; ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 6]);
      ctx.beginPath(); ctx.arc(cx, cy, radii[s], 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
    }

    // Nucleus
    const numP = Math.min(protons,  engine._nucleusProtonPos.length);
    const numN = Math.min(neutrons, engine._nucleusNeutronPos.length);

    for (let i = 0; i < numP; i++) {
      const p = engine._nucleusProtonPos[i];
      const grad = ctx.createRadialGradient(cx + p.dx - 1, cy + p.dy - 1, 0, cx + p.dx, cy + p.dy, 4.5);
      grad.addColorStop(0, '#fca5a5'); grad.addColorStop(1, '#ef4444');
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(cx + p.dx, cy + p.dy, 4.5, 0, Math.PI * 2); ctx.fill();
    }
    for (let i = 0; i < numN; i++) {
      const p = engine._nucleusNeutronPos[i];
      const grad = ctx.createRadialGradient(cx + p.dx - 1, cy + p.dy - 1, 0, cx + p.dx, cy + p.dy, 4);
      grad.addColorStop(0, '#c4b5fd'); grad.addColorStop(1, '#8b5cf6');
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(cx + p.dx, cy + p.dy, 4, 0, Math.PI * 2); ctx.fill();
    }

    // Electrons
    engine.electrons.forEach(function(e) {
      const a  = e.angle + engine.angle * e.speed;
      const ex = cx + e.radius * Math.cos(a);
      const ey = cy + e.radius * Math.sin(a);
      const eGrad = ctx.createRadialGradient(ex - 1, ey - 1, 0, ex, ey, 6);
      eGrad.addColorStop(0, '#7dd3fc'); eGrad.addColorStop(1, '#0ea5e9');
      ctx.shadowBlur = 10; ctx.shadowColor = '#0ea5e9';
      ctx.fillStyle = eGrad;
      ctx.beginPath(); ctx.arc(ex, ey, 5.5, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;
    });

    // Element label in nucleus
    const elem = state.get('element') || '';
    ctx.fillStyle = '#f8fafc'; ctx.font = 'bold 13px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(elem.substring(0, 2), cx, cy + 5);

    // HUD (top-left)
    ctx.fillStyle = 'rgba(15,23,42,0.8)'; ctx.beginPath(); ctx.roundRect(8, 8, 190, 78, 8); ctx.fill();
    ctx.fillStyle = '#f1f5f9'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('Element:  ' + (state.get('element') || '?'),                 16, 28);
    ctx.fillText('Atomic #: ' + (state.get('atomic_number') || 0),             16, 46);
    ctx.fillText('Mass #:   ' + (state.get('mass_number')   || 0),             16, 64);

    // Legend
    ctx.fillStyle = '#ef4444'; ctx.font = '9px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('● Proton', w - 10, h - 28);
    ctx.fillStyle = '#8b5cf6';
    ctx.fillText('● Neutron', w - 10, h - 16);
    ctx.fillStyle = '#0ea5e9';
    ctx.fillText('● Electron', w - 10, h - 4);
  }
}
"""


# ════════════════════════════════════════════════════════════════════════════
# MOLECULAR POLARITY
# Fixed: polarity bar was truncated. Full renderer now included.
# ════════════════════════════════════════════════════════════════════════════

MOLECULAR_POLARITY_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.time = 0;
  }

  update(dt, state) {
    this.time += dt;
    const en1  = state.get('electronegativity_1') || 2.1;
    const en2  = state.get('electronegativity_2') || 3.5;
    const diff = Math.abs(en1 - en2);

    state.set('en_difference',  parseFloat(diff.toFixed(2)));
    state.set('bond_polarity',  diff > 0.4  ? 'Polar'    : 'Non-polar');
    state.set('bond_character', diff > 1.7  ? 'Ionic'    :
                                diff > 0.4  ? 'Polar Cov.' : 'Non-polar Cov.');
  }

  onReset() { this.time = 0; }
  getHint()  { return 'Δ EN > 1.7 → ionic bond  |  0.4–1.7 → polar covalent'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#f0fdf4'; ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    const cx   = w / 2, cy = h / 2 - 20;
    const en1  = state.get('electronegativity_1') || 2.1;
    const en2  = state.get('electronegativity_2') || 3.5;
    const diff = Math.abs(en1 - en2);

    // Atom radii proportional to EN
    const r1 = 32 + en1 * 7;
    const r2 = 32 + en2 * 7;
    const sep = 70;
    const ax1 = cx - sep, ax2 = cx + sep;

    // Electron density cloud (partial charges): bigger blob towards higher EN atom
    if (diff > 0.05) {
      const dir = en2 > en1 ? 1 : -1;
      const cloudX = cx + dir * 20;
      const cGrad  = ctx.createRadialGradient(cloudX, cy, 4, cloudX, cy, 55);
      cGrad.addColorStop(0, 'rgba(99,102,241,0.22)');
      cGrad.addColorStop(1, 'rgba(99,102,241,0)');
      ctx.fillStyle = cGrad;
      ctx.beginPath(); ctx.ellipse(cloudX, cy, 65, 45, 0, 0, Math.PI * 2); ctx.fill();
    }

    // Bond line
    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 5; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(ax1 + r1 * 0.65, cy); ctx.lineTo(ax2 - r2 * 0.65, cy); ctx.stroke();

    // Atom 1
    const a1Grad = ctx.createRadialGradient(ax1 - 6, cy - 6, 4, ax1, cy, r1);
    const c1 = en1 > en2 ? '#fca5a5' : '#bfdbfe';
    a1Grad.addColorStop(0, c1); a1Grad.addColorStop(1, en1 > en2 ? '#ef4444' : '#3b82f6');
    ctx.shadowBlur = 14; ctx.shadowColor = en1 > en2 ? '#ef4444' : '#3b82f6';
    ctx.fillStyle = a1Grad;
    ctx.beginPath(); ctx.arc(ax1, cy, r1, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#fff'; ctx.font = 'bold 12px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('A', ax1, cy - 4);
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 10px sans-serif';
    ctx.fillText('EN=' + en1.toFixed(1), ax1, cy + r1 + 16);

    // Atom 2
    const a2Grad = ctx.createRadialGradient(ax2 - 6, cy - 6, 4, ax2, cy, r2);
    const c2 = en2 > en1 ? '#fca5a5' : '#bfdbfe';
    a2Grad.addColorStop(0, c2); a2Grad.addColorStop(1, en2 > en1 ? '#ef4444' : '#3b82f6');
    ctx.shadowBlur = 14; ctx.shadowColor = en2 > en1 ? '#ef4444' : '#3b82f6';
    ctx.fillStyle = a2Grad;
    ctx.beginPath(); ctx.arc(ax2, cy, r2, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#fff'; ctx.font = 'bold 12px sans-serif';
    ctx.fillText('B', ax2, cy - 4);
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 10px sans-serif';
    ctx.fillText('EN=' + en2.toFixed(1), ax2, cy + r2 + 16);

    // δ+/δ- labels
    if (diff > 0.4) {
      const lowAtom  = en1 < en2 ? ax1 : ax2;
      const highAtom = en1 < en2 ? ax2 : ax1;
      ctx.font = 'bold 14px serif'; ctx.fillStyle = '#dc2626';
      ctx.fillText('δ−', highAtom, cy - r2 * 1.1 - 4);
      ctx.fillStyle = '#2563eb';
      ctx.fillText('δ+', lowAtom,  cy - r1 * 1.1 - 4);

      // Dipole arrow
      const dir = en2 > en1 ? 1 : -1;
      const arrY = cy - Math.max(r1, r2) - 28;
      ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 2.5; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(cx - dir * 30, arrY); ctx.lineTo(cx + dir * 30, arrY); ctx.stroke();
      // arrowhead
      ctx.fillStyle = '#f59e0b';
      ctx.beginPath();
      ctx.moveTo(cx + dir * 30,      arrY - 5);
      ctx.lineTo(cx + dir * 30 + dir * 10, arrY);
      ctx.lineTo(cx + dir * 30,      arrY + 5);
      ctx.closePath(); ctx.fill();
      ctx.font = 'bold 9px sans-serif'; ctx.fillStyle = '#92400e';
      ctx.fillText('μ dipole', cx + dir * 22, arrY - 8);
    }

    // EN scale bar at bottom
    const barX = 20, barY = h - 45, barW = w - 40, barH = 14;
    const barGrad = ctx.createLinearGradient(barX, 0, barX + barW, 0);
    barGrad.addColorStop(0,    '#3b82f6');
    barGrad.addColorStop(0.23, '#22c55e');
    barGrad.addColorStop(0.5,  '#f59e0b');
    barGrad.addColorStop(0.85, '#ef4444');
    barGrad.addColorStop(1,    '#7c3aed');
    ctx.fillStyle = barGrad; ctx.beginPath(); ctx.roundRect(barX, barY, barW, barH, 4); ctx.fill();

    // Markers for en1 and en2 on bar
    [{ val: en1, label: 'A' }, { val: en2, label: 'B' }].forEach(function(m) {
      const mx = barX + ((m.val - 0.5) / 3.5) * barW;
      ctx.fillStyle = '#1e293b';
      ctx.beginPath(); ctx.moveTo(mx, barY - 2); ctx.lineTo(mx - 5, barY - 12); ctx.lineTo(mx + 5, barY - 12); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#1e293b'; ctx.font = 'bold 9px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(m.label, mx, barY - 14);
    });

    ctx.fillStyle = '#475569'; ctx.font = '8px sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('EN 0.5', barX, h - 28);
    ctx.textAlign = 'right'; ctx.fillText('EN 4.0', barX + barW, h - 28);

    // HUD
    ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.beginPath(); ctx.roundRect(8, 8, 185, 72, 8); ctx.fill();
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('ΔEN: ' + (state.get('en_difference') || 0),           16, 28);
    ctx.fillText('Bond: ' + (state.get('bond_character')|| '—'),        16, 46);
    ctx.fillText('Polarity: ' + (state.get('bond_polarity')|| '—'),     16, 64);
  }
}
"""


# ════════════════════════════════════════════════════════════════════════════
# CHEMICAL REACTIONS (Kinetics)
# Fixed: molecules were bouncing off wrong coords; canvas dimensions now used.
# ════════════════════════════════════════════════════════════════════════════

REACTIONS_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.state = state; this.bus = bus;
    this.molecules  = [];
    this.collisions = 0;
    this.time       = 0;
    this._initMolecules(12);
  }

  _initMolecules(count) {
    this.molecules = [];
    const w = this.canvas.width, h = this.canvas.height;
    for (let i = 0; i < count; i++) {
      this.molecules.push({
        x:  20 + Math.random() * (w - 40),
        y:  20 + Math.random() * (h - 40),
        vx: (Math.random() - 0.5) * 80,
        vy: (Math.random() - 0.5) * 80,
        type: i < count / 2 ? 'A' : 'B',
        r:    12 + Math.random() * 5,
        reacted: false,
      });
    }
  }

  update(dt, state) {
    this.time += dt;
    const temp  = state.get('temperature')   || 300;
    const conc  = state.get('concentration') || 50;
    const cat   = state.get('catalyst')      || 0;
    const w     = this.canvas.width, h = this.canvas.height;

    const speed = (temp / 300) * (conc / 50) * (1 + cat * 0.03);

    let frameCollisions = 0;

    this.molecules.forEach(function(m) {
      m.x += m.vx * dt * speed;
      m.y += m.vy * dt * speed;
      if (m.x - m.r < 0)   { m.x = m.r;     m.vx =  Math.abs(m.vx); }
      if (m.x + m.r > w)   { m.x = w - m.r; m.vx = -Math.abs(m.vx); }
      if (m.y - m.r < 0)   { m.y = m.r;     m.vy =  Math.abs(m.vy); }
      if (m.y + m.r > h)   { m.y = h - m.r; m.vy = -Math.abs(m.vy); }
    });

    // Collision detection
    for (let i = 0; i < this.molecules.length; i++) {
      for (let j = i + 1; j < this.molecules.length; j++) {
        const a = this.molecules[i], b = this.molecules[j];
        if (a.type === b.type) continue;
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < a.r + b.r) {
          frameCollisions++;
          // Elastic-ish bounce
          const nx = dx / dist, ny = dy / dist;
          const relV = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny;
          a.vx -= relV * nx; a.vy -= relV * ny;
          b.vx += relV * nx; b.vy += relV * ny;
          // Prevent overlap
          const overlap = (a.r + b.r - dist) / 2;
          a.x += nx * overlap; a.y += ny * overlap;
          b.x -= nx * overlap; b.y -= ny * overlap;
        }
      }
    }

    this.collisions += frameCollisions;

    state.set('temperature',   temp);
    state.set('collision_rate',frameCollisions);
    state.set('reaction_rate', parseFloat((frameCollisions * (temp / 300) * (1 + cat * 0.02)).toFixed(2)));
    state.set('molecules',     this.molecules.length);
  }

  onReset() {
    this.collisions = 0; this.time = 0;
    this._initMolecules(12);
  }

  getHint() { return 'Raise temperature or add catalyst to increase reaction rate'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
    this._rateHistory = [];
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    const temp    = state.get('temperature') || 300;
    const heatFrac = Math.min(1, (temp - 200) / 600);

    // Background tints red as temperature rises
    const r = Math.round(248 + heatFrac * 7);
    const g = Math.round(250 - heatFrac * 30);
    ctx.fillStyle = `rgb(${r},${g},250)`; ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 35) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 35) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    // Molecules
    const engine = window._engine;
    if (engine) {
      engine.molecules.forEach(function(m) {
        const color = m.type === 'A' ? '#3b82f6' : '#ef4444';
        const grd   = ctx.createRadialGradient(m.x - 2, m.y - 2, 1, m.x, m.y, m.r);
        grd.addColorStop(0, m.type === 'A' ? '#93c5fd' : '#fca5a5');
        grd.addColorStop(1, color);
        ctx.fillStyle = grd;
        ctx.beginPath(); ctx.arc(m.x, m.y, m.r, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#fff'; ctx.font = 'bold 9px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText(m.type, m.x, m.y + 3);
      });
    }

    // Reaction rate sparkline (mini bar)
    const rate    = parseFloat(state.get('reaction_rate') || 0);
    this._rateHistory.push(rate);
    if (this._rateHistory.length > 60) this._rateHistory.shift();
    const maxR    = Math.max(1, ...this._rateHistory);
    const barX    = 8, barY = h - 40, barW = 120, barH = 10;
    ctx.fillStyle = '#e2e8f0'; ctx.beginPath(); ctx.roundRect(barX, barY, barW, barH, 3); ctx.fill();
    const fillW   = (rate / maxR) * barW;
    const fillGrad = ctx.createLinearGradient(barX, 0, barX + barW, 0);
    fillGrad.addColorStop(0, '#10b981'); fillGrad.addColorStop(1, '#f59e0b');
    ctx.fillStyle = fillGrad; ctx.beginPath(); ctx.roundRect(barX, barY, fillW, barH, 3); ctx.fill();
    ctx.fillStyle = '#374151'; ctx.font = '8px sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('Reaction Rate →', barX, barY - 4);

    // HUD
    ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.beginPath(); ctx.roundRect(8, 8, 205, 80, 8); ctx.fill();
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('Temp:    '   + temp.toFixed(0) + ' K',                          16, 28);
    ctx.fillText('Coll/frame: '+ (state.get('collision_rate') || 0),              16, 46);
    ctx.fillText('Rate:    '   + (state.get('reaction_rate')  || 0).toFixed(2),   16, 64);

    // Legend
    ctx.fillStyle = '#3b82f6'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText('● Reactant A', w - 10, h - 20);
    ctx.fillStyle = '#ef4444';
    ctx.fillText('● Reactant B', w - 10, h - 8);
    ctx.textAlign = 'left';
  }
}
"""


# ════════════════════════════════════════════════════════════════════════════
# BUILDER
# ════════════════════════════════════════════════════════════════════════════

def build_chemistry_simulation(spec: SimulationSpecification) -> str:
    sim_type = spec.simulation_type.value

    if sim_type == "atomic_structure":
        return _build_atomic_structure(spec)
    elif sim_type == "molecular_polarity":
        return _build_molecular_polarity(spec)
    elif sim_type == "reactions":
        return _build_reactions(spec)
    else:
        return build_simulation_html(spec, custom_script=build_custom_llm_simulation(spec))


def _build_atomic_structure(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Protons (Z) <span class="ctrl-unit">1–18</span></span>
        <span class="val-badge" id="badge-protons">6</span>
      </div>
      <input type="range" id="protons" min="1" max="18" step="1" value="6"
             aria-label="Number of protons (atomic number)">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Neutrons (N) <span class="ctrl-unit"></span></span>
        <span class="val-badge" id="badge-neutrons">6</span>
      </div>
      <input type="range" id="neutrons" min="0" max="20" step="1" value="6"
             aria-label="Number of neutrons">
    </div>"""

    presets = """  <div class="presets">
    <button data-p="1"  data-n="0">H</button>
    <button data-p="2"  data-n="2">He</button>
    <button data-p="6"  data-n="6">C</button>
    <button data-p="8"  data-n="8">O</button>
    <button data-p="11" data-n="12">Na</button>
    <button data-p="17" data-n="18">Cl</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var p = this.getAttribute('data-p'), n = this.getAttribute('data-n');
        function _set(id, val) {
          var el = document.getElementById(id); if (el) el.value = val;
          var bg = document.getElementById('badge-' + id); if (bg) bg.textContent = val;
        }
        _set('protons', p); _set('neutrons', n);
        window._state.set('protons',  parseFloat(p));
        window._state.set('neutrons', parseFloat(n));
      });
    });
"""

    values = """    <div class="vcard"><div class="lbl">Atomic #</div><div class="num" id="val-atomic_number" style="color:#ef4444">6</div></div>
    <div class="vcard"><div class="lbl">Mass #</div><div class="num" id="val-mass_number" style="color:#8b5cf6">12</div></div>
    <div class="vcard"><div class="lbl">Shells</div><div class="num" id="val-shells" style="color:#0ea5e9">2</div></div>
    <div class="vcard"><div class="lbl">Element</div><div class="num" id="val-element" style="color:#10b981; font-size:12px">Carbon</div></div>"""

    return build_simulation_html(
        spec,
        custom_script  = ATOMIC_STRUCTURE_ENGINE + "\n" + presets_script,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment_html(spec),
        custom_presets = presets,
    )


def _build_molecular_polarity(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Atom A Electronegativity <span class="ctrl-unit"></span></span>
        <span class="val-badge" id="badge-electronegativity_1">2.1</span>
      </div>
      <input type="range" id="electronegativity_1" min="0.5" max="4.0" step="0.1" value="2.1"
             aria-label="Electronegativity of atom A">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Atom B Electronegativity <span class="ctrl-unit"></span></span>
        <span class="val-badge" id="badge-electronegativity_2">3.5</span>
      </div>
      <input type="range" id="electronegativity_2" min="0.5" max="4.0" step="0.1" value="3.5"
             aria-label="Electronegativity of atom B">
    </div>"""

    presets = """  <div class="presets">
    <button data-en1="2.1" data-en2="2.1">H–H (non-polar)</button>
    <button data-en1="2.1" data-en2="3.5">H–F (polar)</button>
    <button data-en1="0.9" data-en2="3.5">Na–F (ionic)</button>
    <button data-en1="2.5" data-en2="3.0">C–N</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var en1 = this.getAttribute('data-en1'), en2 = this.getAttribute('data-en2');
        function _set(id, val) {
          var el = document.getElementById(id); if (el) el.value = val;
          var bg = document.getElementById('badge-' + id); if (bg) bg.textContent = val;
        }
        _set('electronegativity_1', en1); _set('electronegativity_2', en2);
        window._state.set('electronegativity_1', parseFloat(en1));
        window._state.set('electronegativity_2', parseFloat(en2));
      });
    });
"""

    values = """    <div class="vcard"><div class="lbl">ΔEN</div><div class="num" id="val-en_difference" style="color:#f59e0b">1.4</div></div>
    <div class="vcard"><div class="lbl">Bond Type</div><div class="num" id="val-bond_character" style="color:#6366f1; font-size:11px">Polar Cov.</div></div>
    <div class="vcard"><div class="lbl">Polarity</div><div class="num" id="val-bond_polarity" style="color:#10b981; font-size:12px">Polar</div></div>"""

    return build_simulation_html(
        spec,
        custom_script  = MOLECULAR_POLARITY_ENGINE + "\n" + presets_script,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment_html(spec),
        custom_presets = presets,
    )


def _build_reactions(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Temperature (T) <span class="ctrl-unit">K</span></span>
        <span class="val-badge" id="badge-temperature">300</span>
      </div>
      <input type="range" id="temperature" min="200" max="800" step="10" value="300"
             aria-label="Reaction temperature">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Concentration <span class="ctrl-unit">%</span></span>
        <span class="val-badge" id="badge-concentration">50</span>
      </div>
      <input type="range" id="concentration" min="10" max="100" step="5" value="50"
             aria-label="Reactant concentration">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Catalyst <span class="ctrl-unit">0→10</span></span>
        <span class="val-badge" id="badge-catalyst">0</span>
      </div>
      <input type="range" id="catalyst" min="0" max="10" step="1" value="0"
             aria-label="Catalyst amount">
    </div>"""

    values = """    <div class="vcard"><div class="lbl">Temperature (K)</div><div class="num" id="val-temperature" style="color:#ef4444">300</div></div>
    <div class="vcard"><div class="lbl">Collision Rate</div><div class="num" id="val-collision_rate" style="color:#f59e0b">0</div></div>
    <div class="vcard"><div class="lbl">Reaction Rate</div><div class="num" id="val-reaction_rate" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Molecules</div><div class="num" id="val-molecules" style="color:#10b981">12</div></div>"""

    return build_simulation_html(
        spec,
        custom_script  = REACTIONS_ENGINE,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment_html(spec),
    )