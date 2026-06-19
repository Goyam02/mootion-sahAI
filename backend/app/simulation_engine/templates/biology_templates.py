from __future__ import annotations

from app.simulation_engine.schemas import SimulationSpecification
from app.simulation_engine.templates.base_template import (
    build_simulation_html,
    build_custom_llm_simulation,
    _build_assessment_html,
)


# ════════════════════════════════════════════════════════════════════════════
# DIFFUSION
# Fixed: forEach callbacks used `this` without binding → particles.forEach
# used this.canvas.width inside an unbound function → always undefined.
# ════════════════════════════════════════════════════════════════════════════

DIFFUSION_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas    = canvas;
    this.state     = state;
    this.bus       = bus;
    this.particles = [];
    this._dirty    = true;   // force reinit on first frame
  }

  _initParticles(conc, particleSize) {
    const w = this.canvas.width, h = this.canvas.height;
    const total = Math.round(Math.max(10, conc * 0.8));
    this.particles = [];
    for (let i = 0; i < total; i++) {
      // 70% start on the left side (high concentration)
      const onLeft = i < total * 0.7;
      const x      = onLeft
        ? 10  + Math.random() * (w / 2 - 20)
        : w / 2 + 10 + Math.random() * (w / 2 - 20);
      this.particles.push({
        x, y:  30 + Math.random() * (h - 60),
        vx: (Math.random() - 0.5) * 80,
        vy: (Math.random() - 0.5) * 80,
        r:  2.5 + (particleSize / 10) * 3,
      });
    }
    this._dirty = false;
  }

  update(dt, state) {
    const temp         = state.get('temperature')   || 300;
    const conc         = state.get('concentration') || 50;
    const particleSize = state.get('particle_size') || 5;

    if (this._dirty || this.particles.length === 0) {
      this._initParticles(conc, particleSize);
    }

    const w   = this.canvas.width, h = this.canvas.height;
    const spd = (temp / 300) * (5 / (particleSize + 1));

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      p.x += p.vx * dt * spd;
      p.y += p.vy * dt * spd;
      // Wall reflections
      if (p.x - p.r < 0)   { p.x = p.r;     p.vx =  Math.abs(p.vx); }
      if (p.x + p.r > w)   { p.x = w - p.r; p.vx = -Math.abs(p.vx); }
      if (p.y - p.r < 30)  { p.y = 30 + p.r; p.vy = Math.abs(p.vy); }
      if (p.y + p.r > h - 30) { p.y = h - 30 - p.r; p.vy = -Math.abs(p.vy); }
    }

    const mx    = w / 2;
    let   left  = 0, right = 0;
    for (let i = 0; i < this.particles.length; i++) {
      if (this.particles[i].x < mx) left++; else right++;
    }
    state.set('left_count',  left);
    state.set('right_count', right);
    state.set('flux',        Math.abs(left - right));
    state.set('equilibrium', left === right ? 1 : 0);
  }

  onReset() { this._dirty = true; }

  getHint() { return 'Particles move from high → low concentration until equilibrium'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
    this._fluxHistory = [];
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Compartment backgrounds
    ctx.fillStyle = 'rgba(59,130,246,0.06)';  ctx.fillRect(0, 0, w / 2, h);
    ctx.fillStyle = 'rgba(244,63,94,0.06)';   ctx.fillRect(w / 2, 0, w / 2, h);

    // Grid
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    const mx = w / 2;

    // Membrane (semi-permeable)
    ctx.strokeStyle = '#8b5cf6'; ctx.lineWidth = 4; ctx.setLineDash([12, 6]);
    ctx.beginPath(); ctx.moveTo(mx, 20); ctx.lineTo(mx, h - 20); ctx.stroke();
    ctx.setLineDash([]);

    // Membrane pores
    for (let y = 60; y < h - 40; y += 55) {
      ctx.fillStyle = '#f8fafc';
      ctx.fillRect(mx - 6, y - 7, 12, 14);
      ctx.strokeStyle = '#a78bfa'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.rect(mx - 6, y - 7, 12, 14); ctx.stroke();
    }

    // Membrane label
    ctx.fillStyle = '#7c3aed'; ctx.font = 'bold 9px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('SEMI-PERMEABLE', mx, 14);
    ctx.fillText('MEMBRANE', mx, 24);

    // Particles
    const engine = window._engine;
    if (engine) {
      for (let i = 0; i < engine.particles.length; i++) {
        const p    = engine.particles[i];
        const onLeft = p.x < mx;
        const color  = onLeft ? '#3b82f6' : '#f43f5e';
        const grd    = ctx.createRadialGradient(p.x - 1, p.y - 1, 0, p.x, p.y, p.r);
        grd.addColorStop(0, onLeft ? '#93c5fd' : '#fda4af');
        grd.addColorStop(1, color);
        ctx.fillStyle = grd;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
      }
    }

    // Concentration labels
    const left  = state.get('left_count')  || 0;
    const right = state.get('right_count') || 0;
    ctx.fillStyle = 'rgba(59,130,246,0.12)'; ctx.beginPath(); ctx.roundRect(4, h - 42, w / 2 - 8, 36, 6); ctx.fill();
    ctx.fillStyle = 'rgba(244,63,94,0.12)';  ctx.beginPath(); ctx.roundRect(w / 2 + 4, h - 42, w / 2 - 8, 36, 6); ctx.fill();
    ctx.fillStyle = '#1e40af'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'center';
    ctx.fillText('Left: ' + left + ' particles', w / 4, h - 20);
    ctx.fillStyle = '#be123c';
    ctx.fillText('Right: ' + right + ' particles', w * 3 / 4, h - 20);

    // Flux bar (top-right mini)
    const flux = state.get('flux') || 0;
    this._fluxHistory.push(flux);
    if (this._fluxHistory.length > 80) this._fluxHistory.shift();
    const maxFlux = Math.max(1, ...this._fluxHistory);
    const barW = 100, barH = 10, barX = w - 115, barY = 35;
    ctx.fillStyle = '#e2e8f0'; ctx.beginPath(); ctx.roundRect(barX, barY, barW, barH, 3); ctx.fill();
    ctx.fillStyle = '#8b5cf6';
    ctx.beginPath(); ctx.roundRect(barX, barY, (flux / maxFlux) * barW, barH, 3); ctx.fill();
    ctx.fillStyle = '#4c1d95'; ctx.font = '8px sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('Net flux: ' + flux, barX, barY - 4);

    if (left === right) {
      ctx.fillStyle = '#059669'; ctx.font = 'bold 12px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText('⚖ Equilibrium reached!', w / 2, 45);
    }
    ctx.textAlign = 'left';
  }
}
"""


# ════════════════════════════════════════════════════════════════════════════
# POPULATION GROWTH (Logistic)
# Previously incomplete / truncated. Now full and polished with S-curve graph.
# ════════════════════════════════════════════════════════════════════════════

POPULATION_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas     = canvas;
    this.state      = state;
    this.bus        = bus;
    this.time       = 0;
    this.popHistory = [];   // {t, pop} for drawing the S-curve
  }

  update(dt, state) {
    this.time += dt;
    const birthRate = state.get('birth_rate')        || 0.5;
    const deathRate = state.get('death_rate')         || 0.3;
    const carrying  = state.get('carrying_capacity') || 500;
    let   pop       = state.get('population');
    if (pop === undefined || pop === null) pop = 10;

    const r           = birthRate - deathRate;
    const logisticDot = r * pop * (1 - pop / carrying);
    pop              += logisticDot * dt * 10;
    pop               = Math.max(0, Math.min(carrying * 2, pop));

    const births = birthRate * pop * dt * 10;
    const deaths = deathRate * pop * dt * 10;

    state.set('population',   parseFloat(pop.toFixed(1)));
    state.set('growth_rate',  parseFloat(logisticDot.toFixed(3)));
    state.set('births',       parseFloat(births.toFixed(1)));
    state.set('deaths',       parseFloat(deaths.toFixed(1)));
    state.set('r',            parseFloat(r.toFixed(3)));

    this.popHistory.push({ t: this.time, pop });
    if (this.popHistory.length > 600) this.popHistory.shift();
  }

  onReset() {
    this.time = 0;
    this.popHistory = [];
    this.state.set('population', 10);
  }

  getHint() { return 'Population grows logistically — slows near carrying capacity K'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
    bgGrad.addColorStop(0, '#f0fdf4'); bgGrad.addColorStop(1, '#f8fafc');
    ctx.fillStyle = bgGrad; ctx.fillRect(0, 0, w, h);

    const pop      = state.get('population')       || 0;
    const cap      = state.get('carrying_capacity')|| 500;
    const births   = state.get('births')           || 0;
    const deaths   = state.get('deaths')           || 0;

    // --- S-curve graph ---
    const pad  = { t: 30, r: 20, b: 50, l: 52 };
    const gw   = w - pad.l - pad.r;
    const gh   = h - pad.t - pad.b;
    const engine = window._engine;

    // Axes
    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(pad.l, pad.t); ctx.lineTo(pad.l, pad.t + gh); ctx.lineTo(pad.l + gw, pad.t + gh); ctx.stroke();

    // Grid
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.7;
    for (let i = 1; i <= 4; i++) {
      const y = pad.t + gh - (i / 4) * gh;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(pad.l + gw, y); ctx.stroke();
    }

    // K line
    const kY = pad.t + gh - (cap / (cap * 1.1)) * gh;
    ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 1.5; ctx.setLineDash([6, 5]);
    ctx.beginPath(); ctx.moveTo(pad.l, kY); ctx.lineTo(pad.l + gw, kY); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#ef4444'; ctx.font = 'bold 9px sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('K=' + cap.toFixed(0), pad.l + 4, kY - 4);

    // Y axis labels
    ctx.fillStyle = '#64748b'; ctx.font = '9px "Courier New", monospace'; ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
      const val = (cap * 1.1 * i / 4);
      const y   = pad.t + gh - (i / 4) * gh;
      ctx.fillText(val.toFixed(0), pad.l - 4, y + 3);
    }
    ctx.fillStyle = '#475569'; ctx.font = '9px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('Time →', pad.l + gw / 2, pad.t + gh + 16);
    ctx.save(); ctx.translate(12, pad.t + gh / 2); ctx.rotate(-Math.PI / 2);
    ctx.fillText('Population', 0, 0); ctx.restore();

    // Population curve
    if (engine && engine.popHistory.length > 1) {
      const hist     = engine.popHistory;
      const maxT     = Math.max(hist[hist.length - 1].t, 10);
      const maxPop   = cap * 1.1;

      const popGrad = ctx.createLinearGradient(pad.l, pad.t, pad.l, pad.t + gh);
      popGrad.addColorStop(0, '#22c55e'); popGrad.addColorStop(1, '#4ade80');
      ctx.strokeStyle = popGrad; ctx.lineWidth = 2.5; ctx.lineJoin = 'round';
      ctx.beginPath();
      for (let i = 0; i < hist.length; i++) {
        const px = pad.l + (hist[i].t / maxT) * gw;
        const py = pad.t + gh - Math.min(1, hist[i].pop / maxPop) * gh;
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      }
      ctx.stroke();

      // Fill under curve
      ctx.save();
      ctx.beginPath();
      for (let i = 0; i < hist.length; i++) {
        const px = pad.l + (hist[i].t / maxT) * gw;
        const py = pad.t + gh - Math.min(1, hist[i].pop / maxPop) * gh;
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      }
      ctx.lineTo(pad.l + (hist[hist.length - 1].t / maxT) * gw, pad.t + gh);
      ctx.lineTo(pad.l, pad.t + gh);
      ctx.closePath();
      ctx.fillStyle = 'rgba(34,197,94,0.12)'; ctx.fill();
      ctx.restore();
    }

    // Current population dot
    if (engine && engine.popHistory.length > 0) {
      const hist  = engine.popHistory;
      const maxT  = Math.max(hist[hist.length - 1].t, 10);
      const last  = hist[hist.length - 1];
      const dotX  = pad.l + (last.t / maxT) * gw;
      const dotY  = pad.t + gh - Math.min(1, last.pop / (cap * 1.1)) * gh;
      ctx.fillStyle = '#16a34a'; ctx.shadowBlur = 10; ctx.shadowColor = '#22c55e';
      ctx.beginPath(); ctx.arc(dotX, dotY, 5, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;
    }

    // HUD box top-right
    ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.beginPath(); ctx.roundRect(w - 178, 8, 166, 82, 8); ctx.fill();
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('Pop:    ' + pop.toFixed(0),                                    w - 168, 28);
    ctx.fillText('r:      ' + (state.get('r') || 0).toFixed(3),                 w - 168, 46);
    ctx.fillText('dN/dt:  ' + (state.get('growth_rate') || 0).toFixed(2),       w - 168, 64);

    // Births/Deaths indicators
    const indicatorX = pad.l + 10;
    ctx.fillStyle = '#16a34a'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('▲ Births: ' + births.toFixed(1), indicatorX, h - 10);
    ctx.fillStyle = '#dc2626';
    ctx.fillText('▼ Deaths: ' + deaths.toFixed(1), indicatorX + 110, h - 10);
  }
}
"""


# ════════════════════════════════════════════════════════════════════════════
# MEMBRANE TRANSPORT (Active/Passive)
# Improved visual — two-compartment cell with animated proteins.
# ════════════════════════════════════════════════════════════════════════════

MEMBRANE_TRANSPORT_ENGINE = """
class SimulationEngine {
  constructor(canvas, state, bus) {
    this.canvas          = canvas;
    this.state           = state;
    this.bus             = bus;
    this.time            = 0;
    this.particles       = [];
    this.proteins        = [];
    this.transportedCount= 0;
    this._initParticles();
    this._initProteins(3);
  }

  _initParticles() {
    const w = this.canvas.width, h = this.canvas.height;
    const mx = w / 2;
    this.particles = [];
    for (let i = 0; i < 40; i++) {
      const out = i < 28;  // 70% outside
      this.particles.push({
        x:    out ? 10 + Math.random() * (mx - 30) : mx + 20 + Math.random() * (w - mx - 30),
        y:    40 + Math.random() * (h - 80),
        vx:   (Math.random() - 0.5) * 50,
        vy:   (Math.random() - 0.5) * 50,
        side: out ? 'out' : 'in',
        transported: false,
      });
    }
  }

  _initProteins(count) {
    const h = this.canvas.height;
    this.proteins = [];
    for (let i = 0; i < count; i++) {
      this.proteins.push({
        y:        80 + i * ((h - 120) / count),
        open:     false,
        openTime: 0,
      });
    }
  }

  update(dt, state) {
    this.time += dt;
    const gradient = state.get('concentration_gradient') || 50;
    const atp      = state.get('atp_available')          || 50;
    const perm     = state.get('permeability')           || 50;
    const w        = this.canvas.width, h = this.canvas.height;
    const mx       = w / 2;

    // Move particles
    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      if (p.y < 40 || p.y > h - 40) p.vy *= -1;
      if (p.x < 5)     { p.x = 5;     p.vx =  Math.abs(p.vx); }
      if (p.x > w - 5) { p.x = w - 5; p.vx = -Math.abs(p.vx); }
    }

    // Open/close channel proteins
    for (let i = 0; i < this.proteins.length; i++) {
      const pr = this.proteins[i];
      if (!pr.open && Math.random() < perm * 0.003) {
        pr.open = true; pr.openTime = 0.4;
      }
      if (pr.open) {
        pr.openTime -= dt;
        if (pr.openTime <= 0) pr.open = false;
      }
    }

    // Transport through open channels
    for (let pi = 0; pi < this.particles.length; pi++) {
      const p = this.particles[pi];
      for (let pr = 0; pr < this.proteins.length; pr++) {
        const protein = this.proteins[pr];
        if (!protein.open) continue;
        const dy = Math.abs(p.y - protein.y);
        const dx = Math.abs(p.x - mx);
        if (dx < 14 && dy < 14) {
          // Gradient-driven: outside → inside if gradient > 50
          if (p.side === 'out' && gradient > 30 && Math.random() < 0.05) {
            p.side        = 'in';
            p.transported = true;
            p.x           = mx + 20;
            this.transportedCount++;
          } else if (p.side === 'in' && gradient < 30 && Math.random() < 0.02) {
            p.side        = 'out';
            p.x           = mx - 20;
          }
        }
      }
    }

    state.set('transported',     this.transportedCount);
    state.set('atp_consumed',    Math.round(this.transportedCount * (atp / 100) * 0.5));
    state.set('outside_count',   this.particles.filter(function(p) { return p.side === 'out'; }).length);
    state.set('inside_count',    this.particles.filter(function(p) { return p.side === 'in';  }).length);
  }

  onReset() {
    this.transportedCount = 0; this.time = 0;
    this._initParticles();
    this._initProteins(3);
    this.state.set('transported', 0);
  }

  getHint() { return 'Raise concentration gradient or permeability to speed transport'; }
}

class Renderer {
  constructor(canvas, state, bus) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.state = state; this.bus = bus;
  }

  draw(dt, state) {
    const ctx = this.ctx, w = this.canvas.width, h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);
    const mx = w / 2;

    // Compartment fills
    ctx.fillStyle = 'rgba(219,234,254,0.45)'; ctx.fillRect(0, 0, mx - 12, h);
    ctx.fillStyle = 'rgba(220,252,231,0.45)'; ctx.fillRect(mx + 12, 0, w - mx - 12, h);

    // Grid
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 35) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 35) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    // Membrane (phospholipid bilayer look)
    const membGrad = ctx.createLinearGradient(mx - 14, 0, mx + 14, 0);
    membGrad.addColorStop(0,   '#a78bfa');
    membGrad.addColorStop(0.35,'#7c3aed');
    membGrad.addColorStop(0.65,'#7c3aed');
    membGrad.addColorStop(1,   '#a78bfa');
    ctx.fillStyle = membGrad;
    ctx.fillRect(mx - 14, 0, 28, h);

    // Membrane label
    ctx.fillStyle = '#f8fafc'; ctx.font = 'bold 8px sans-serif'; ctx.textAlign = 'center';
    ctx.save(); ctx.translate(mx, h / 2); ctx.rotate(-Math.PI / 2);
    ctx.fillText('PHOSPHOLIPID BILAYER', 0, 0); ctx.restore();

    // Compartment labels
    ctx.fillStyle = '#1e40af'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('Extracellular', mx / 2, 18);
    ctx.fillStyle = '#15803d';
    ctx.fillText('Intracellular', mx + (w - mx) / 2, 18);

    // Channel proteins
    const engine = window._engine;
    if (engine) {
      engine.proteins.forEach(function(protein) {
        const py = protein.y;
        const openColor  = protein.open ? '#fbbf24' : '#f59e0b';
        const pGrad = ctx.createLinearGradient(mx - 14, py - 14, mx + 14, py + 14);
        pGrad.addColorStop(0, '#fde68a'); pGrad.addColorStop(1, openColor);

        ctx.fillStyle = pGrad;
        ctx.beginPath();
        if (protein.open) {
          // Open — show pore
          ctx.roundRect(mx - 13, py - 16, 11, 32, [4, 0, 0, 4]); ctx.fill();
          ctx.beginPath(); ctx.roundRect(mx + 2, py - 16, 11, 32, [0, 4, 4, 0]); ctx.fill();
          ctx.strokeStyle = '#d97706'; ctx.lineWidth = 1;
          ctx.strokeRect(mx - 13, py - 16, 11, 32);
          ctx.strokeRect(mx + 2, py - 16, 11, 32);
        } else {
          ctx.roundRect(mx - 13, py - 14, 26, 28, 4); ctx.fill();
          ctx.strokeStyle = '#92400e'; ctx.lineWidth = 1; ctx.stroke();
        }
        // Label
        ctx.fillStyle = '#1c1917'; ctx.font = 'bold 7px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText(protein.open ? 'OPEN' : 'CHAN', mx, py + 3);
      });

      // Particles
      engine.particles.forEach(function(p) {
        const isOut     = p.side === 'out';
        const color     = isOut ? '#3b82f6' : '#22c55e';
        const grd       = ctx.createRadialGradient(p.x - 1, p.y - 1, 0, p.x, p.y, 5);
        grd.addColorStop(0, isOut ? '#93c5fd' : '#86efac');
        grd.addColorStop(1, color);
        ctx.fillStyle   = grd;
        ctx.beginPath(); ctx.arc(p.x, p.y, 5, 0, Math.PI * 2); ctx.fill();
        if (p.transported) {
          ctx.strokeStyle = '#fbbf24'; ctx.lineWidth = 2;
          ctx.beginPath(); ctx.arc(p.x, p.y, 8, 0, Math.PI * 2); ctx.stroke();
        }
      });
    }

    // Stats bar
    const outCount = state.get('outside_count')   || 0;
    const inCount  = state.get('inside_count')    || 0;
    const trans    = state.get('transported')     || 0;
    ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.beginPath(); ctx.roundRect(8, h - 52, 190, 46, 8); ctx.fill();
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 10px "Courier New", monospace'; ctx.textAlign = 'left';
    ctx.fillText('Out: ' + outCount + '  →  In: ' + inCount, 16, h - 34);
    ctx.fillText('Total transported: ' + trans,               16, h - 18);

    ctx.textAlign = 'left';
  }
}
"""


# ════════════════════════════════════════════════════════════════════════════
# BUILDER
# ════════════════════════════════════════════════════════════════════════════

def build_biology_simulation(spec: SimulationSpecification) -> str:
    sim_type = spec.simulation_type.value

    if sim_type == "diffusion":
        return _build_diffusion(spec)
    elif sim_type == "population_growth":
        return _build_population(spec)
    elif sim_type == "membrane_transport":
        return _build_membrane_transport(spec)
    else:
        return build_simulation_html(spec, custom_script=build_custom_llm_simulation(spec))


def _build_diffusion(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Temperature (T) <span class="ctrl-unit">K</span></span>
        <span class="val-badge" id="badge-temperature">300</span>
      </div>
      <input type="range" id="temperature" min="100" max="600" step="10" value="300"
             aria-label="Temperature in Kelvin">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Concentration <span class="ctrl-unit">particles</span></span>
        <span class="val-badge" id="badge-concentration">50</span>
      </div>
      <input type="range" id="concentration" min="10" max="100" step="5" value="50"
             aria-label="Particle count">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Particle Size <span class="ctrl-unit">1–10</span></span>
        <span class="val-badge" id="badge-particle_size">5</span>
      </div>
      <input type="range" id="particle_size" min="1" max="10" step="1" value="5"
             aria-label="Relative particle size (larger = slower diffusion)">
    </div>"""

    presets_script = """
    // Reinitialise particles when sliders change
    ['temperature', 'concentration', 'particle_size'].forEach(function(id) {
      var el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', function() {
          var engine = window._engine;
          if (engine) engine._dirty = true;
        });
      }
    });
"""

    values = """    <div class="vcard"><div class="lbl">Left Side</div><div class="num" id="val-left_count" style="color:#3b82f6">0</div></div>
    <div class="vcard"><div class="lbl">Right Side</div><div class="num" id="val-right_count" style="color:#f43f5e">0</div></div>
    <div class="vcard"><div class="lbl">Net Flux</div><div class="num" id="val-flux" style="color:#8b5cf6">0</div></div>"""

    return build_simulation_html(
        spec,
        custom_script  = DIFFUSION_ENGINE + "\n" + presets_script,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment_html(spec),
    )


def _build_population(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Birth Rate (b) <span class="ctrl-unit">per ind./t</span></span>
        <span class="val-badge" id="badge-birth_rate">0.50</span>
      </div>
      <input type="range" id="birth_rate" min="0.05" max="1.5" step="0.05" value="0.5"
             aria-label="Per-capita birth rate">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Death Rate (d) <span class="ctrl-unit">per ind./t</span></span>
        <span class="val-badge" id="badge-death_rate">0.30</span>
      </div>
      <input type="range" id="death_rate" min="0.05" max="1.5" step="0.05" value="0.3"
             aria-label="Per-capita death rate">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Carrying Capacity (K) <span class="ctrl-unit">individuals</span></span>
        <span class="val-badge" id="badge-carrying_capacity">500</span>
      </div>
      <input type="range" id="carrying_capacity" min="50" max="2000" step="50" value="500"
             aria-label="Carrying capacity">
    </div>"""

    presets = """  <div class="presets">
    <button data-b="0.5"  data-d="0.3" data-k="500">Logistic Growth</button>
    <button data-b="0.8"  data-d="0.1" data-k="500">Boom!</button>
    <button data-b="0.3"  data-d="0.8" data-k="500">Decline</button>
    <button data-b="0.5"  data-d="0.5" data-k="500">Stable</button>
  </div>"""

    presets_script = """
    document.querySelectorAll('.presets button').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var b = this.getAttribute('data-b'), d = this.getAttribute('data-d');
        var k = this.getAttribute('data-k');
        function _set(id, val) {
          var el = document.getElementById(id); if (el) el.value = val;
          var bg = document.getElementById('badge-' + id); if (bg) bg.textContent = val;
        }
        _set('birth_rate', b); _set('death_rate', d); _set('carrying_capacity', k);
        window._state.set('birth_rate',        parseFloat(b));
        window._state.set('death_rate',        parseFloat(d));
        window._state.set('carrying_capacity', parseFloat(k));
        // Reset population to small starting value
        window._state.set('population', 10);
        var engine = window._engine;
        if (engine) { engine.time = 0; engine.popHistory = []; }
      });
    });
"""

    values = """    <div class="vcard"><div class="lbl">Population</div><div class="num" id="val-population" style="color:#22c55e">10</div></div>
    <div class="vcard"><div class="lbl">Growth dN/dt</div><div class="num" id="val-growth_rate" style="color:#6366f1">0</div></div>
    <div class="vcard"><div class="lbl">Births</div><div class="num" id="val-births" style="color:#10b981">0</div></div>
    <div class="vcard"><div class="lbl">Deaths</div><div class="num" id="val-deaths" style="color:#ef4444">0</div></div>
    <div class="vcard"><div class="lbl">r (b−d)</div><div class="num" id="val-r" style="color:#f59e0b">0</div></div>"""

    return build_simulation_html(
        spec,
        custom_script  = POPULATION_ENGINE + "\n" + presets_script,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment_html(spec),
        custom_presets = presets,
    )


def _build_membrane_transport(spec: SimulationSpecification) -> str:
    controls = """    <div class="ctrl">
      <div class="ctrl-label">
        <span>Concentration Gradient <span class="ctrl-unit">%</span></span>
        <span class="val-badge" id="badge-concentration_gradient">50</span>
      </div>
      <input type="range" id="concentration_gradient" min="0" max="100" step="5" value="50"
             aria-label="Concentration gradient driving force">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>ATP Available <span class="ctrl-unit">%</span></span>
        <span class="val-badge" id="badge-atp_available">50</span>
      </div>
      <input type="range" id="atp_available" min="0" max="100" step="5" value="50"
             aria-label="ATP energy available for active transport">
    </div>
    <div class="ctrl">
      <div class="ctrl-label">
        <span>Membrane Permeability <span class="ctrl-unit">%</span></span>
        <span class="val-badge" id="badge-permeability">50</span>
      </div>
      <input type="range" id="permeability" min="0" max="100" step="5" value="50"
             aria-label="Membrane channel permeability">
    </div>"""

    values = """    <div class="vcard"><div class="lbl">Outside</div><div class="num" id="val-outside_count" style="color:#3b82f6">0</div></div>
    <div class="vcard"><div class="lbl">Inside</div><div class="num" id="val-inside_count" style="color:#22c55e">0</div></div>
    <div class="vcard"><div class="lbl">Transported</div><div class="num" id="val-transported" style="color:#f59e0b">0</div></div>
    <div class="vcard"><div class="lbl">ATP Used</div><div class="num" id="val-atp_consumed" style="color:#8b5cf6">0</div></div>"""

    return build_simulation_html(
        spec,
        custom_script  = MEMBRANE_TRANSPORT_ENGINE,
        custom_controls= controls,
        custom_live_values=values,
        custom_assessment=_build_assessment_html(spec),
    )