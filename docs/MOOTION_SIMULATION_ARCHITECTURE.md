# Mootion Simulation Generation Pipeline

## Architecture Overview

```
Student Prompt ("Explain projectile motion")
       │
       ▼
┌────────────────────────────────────────────────────┐
│           1. PROMPT UNDERSTANDING LAYER             │
│   ┌──────────┬───────────┬──────────┬──────────┐   │
│   │ Subject  │  Topic    │ Concepts │ Sim Type │   │
│   │ Physics  │Projectile │velocity, │projectile│   │
│   │          │ Motion    │angle,grav│_motion   │   │
│   └──────────┴───────────┴──────────┴──────────┘   │
└──────────────────┬─────────────────────────────────┘
                   │ SimulationIntent
                   ▼
┌────────────────────────────────────────────────────┐
│           2. SIMULATION PLANNING LAYER              │
│   Generates structured JSON specification with:     │
│   • Learning objectives         • Parameters        │
│   • Entities                   • Equations          │
│   • Constraints                • Visualizations     │
│   • Graphs                     • Assessment prompts │
└──────────────────┬─────────────────────────────────┘
                   │ SimulationSpecification
                   ▼
┌────────────────────────────────────────────────────┐
│           3. SIMULATION BUILDER LAYER               │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│   │ Physics  │ │Chemistry │ │ Biology  │           │
│   │Templates │ │Templates │ │Templates │           │
│   └──────────┘ └──────────┘ └──────────┘          │
│   ┌──────────┐ ┌─────────────────────────┐        │
│   │   Math   │ │   Base HTML Generator   │        │
│   │Templates │ │   (Canvas + Modules)    │        │
│   └──────────┘ └─────────────────────────┘        │
└──────────────────┬─────────────────────────────────┘
                   │ Self-contained HTML
                   ▼
┌────────────────────────────────────────────────────┐
│           4. SCIENTIFIC VALIDATION LAYER            │
│   • Equation correctness     • Unit validation      │
│   • Range checking           • Domain-specific      │
│   • Physical/chemical/biological accuracy          │
└──────────────────┬─────────────────────────────────┘
                   │ ValidationResult
                   ▼
┌────────────────────────────────────────────────────┐
│           5. UI QUALITY LAYER                       │
│   • Responsive design   • Accessibility            │
│   • Animation quality   • Educational layout       │
│   • Touch/mobile support                           │
└──────────────────┬─────────────────────────────────┘
                   │ Quality Score
                   ▼
┌────────────────────────────────────────────────────┐
│           6. ASSESSMENT LAYER                       │
│   • Prediction prompts       • Inquiry prompts     │
│   • Experimentation tasks    • Reflection prompts  │
└──────────────────┬─────────────────────────────────┘
                   │
                   ▼
          Playable HTML Simulation
          ┌─────────────────────┐
          │ • Interactive canvas│
          │ • Parameter sliders │
          │ • Live value readout│
          │ • Real-time graphs  │
          │ • Assessment prompts│
          │ • Play/Pause/Reset  │
          └─────────────────────┘
```

## Data Flow

```
Prompt → SimulationIntent → SimulationSpecification → HTML → Validated → Playable
   │            │                     │                  │          │
   │            │                     │                  │          ▼
   │            │                     │                  │    Assessment
   │            │                     │                  │    Prompts
   │            │                     │                  │
   ▼            ▼                     ▼                  ▼
LLM        LLM + Rules           Template +         Equation +    
Classifier  Spec Designer        JS Generator       Unit Checks
```

## Folder Structure

```
backend/app/simulation_engine/
├── __init__.py                 # Public API exports
├── schemas.py                  # Pydantic models (SimulationIntent, Spec, etc.)
├── pipeline.py                 # Main pipeline orchestrator
├── prompt_understanding_layer.py  # Subject/type classification
├── simulation_planning_layer.py   # Spec generation
├── simulation_builder.py          # HTML generation dispatcher
├── scientific_validation.py       # Science accuracy verification
├── ui_quality_layer.py            # UI/UX quality checks
├── assessment_layer.py            # Learning prompt generation
├── llm_prompts.py                 # Centralized LLM prompts
├── agent_workflows.py             # Workflow modes (full_auto, template, etc.)
└── templates/
    ├── __init__.py
    ├── base_template.py           # Base HTML + JS framework
    ├── physics_templates.py       # Projectile, Electricity, Waves, Forces
    ├── chemistry_templates.py     # Atomic Structure, Polarity, Reactions
    ├── biology_templates.py       # Diffusion, Population, Membrane Transport
    └── math_templates.py          # Functions, Probability, Statistics, Geometry

backend/app/api/
└── simulation.py              # REST API endpoints

mootion-frontend/src/
├── components/
│   └── MootionSimulationPlayer.tsx  # Iframe-based simulation renderer
└── pages/student/
    └── SimulationGenerator.tsx      # AI prompt → simulation UI
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/simulations/generate` | Generate sim from natural language prompt |
| POST | `/simulations/generate-from-spec` | Generate sim from structured spec |
| GET | `/simulations/supported-subjects` | List supported subjects and topics |
| GET | `/simulations/example-prompts` | Get example prompts |
| GET | `/simulations/{id}` | Get simulation metadata |
| GET | `/simulations/{id}/html` | Get rendered HTML |
| POST | `/simulations/{id}/assess` | Get assessment prompts |

## Generated HTML Architecture

Every simulation HTML is a self-contained document with:

### JavaScript Modules

```javascript
class EventBus { }           // Pub/sub event system
class StateManager { }       // Centralized state with change tracking
class SimulationEngine { }   // Physics/chemistry/biology logic (update)
class Renderer { }           // Canvas 2D rendering (draw)
class ControlsManager { }    // Slider/button bindings
class GraphManager { }       // Real-time data plotting
class AssessmentEngine { }   // Learning prompts
```

### HTML Structure

```html
<div id="sim-container">
  <div class="sim-header">       <!-- Title + Learning Objective -->
  <div class="sim-body">
    <div class="sim-visual">     <!-- Canvas -->
    <div class="sim-panel">      <!-- Sliders + Buttons + Values -->
  </div>
  <div class="graph-area">       <!-- Real-time graph -->
  <div class="assess-area">      <!-- Assessment prompts -->
</div>
```

### Render Loop

```javascript
function loop(time) {
  const dt = (time - lastTime) / 1000;
  if (running) {
    engine.update(dt, state);    // Physics/logic
    graphMgr.pushData(series,    // Record graph data
                      x, y);
  }
  renderer.draw(dt, state);      // Canvas rendering
  graphMgr.draw();               // Graph rendering
  requestAnimationFrame(loop);
}
```

## Supported Simulation Types

### Physics
- **Projectile Motion**: angle, velocity, gravity, mass, trajectory
- **Ohm's Law**: voltage, resistance, current, power, circuit visualization
- **Wave Propagation**: amplitude, frequency, speed, superposition
- **Forces & Motion**: applied force, friction, mass, acceleration
- **Energy**: kinetic/potential energy, conservation, pendulum

### Chemistry
- **Atomic Structure**: protons, neutrons, electrons, shells, element info
- **Molecular Polarity**: electronegativity, dipole moment, bond type
- **Chemical Reactions**: temperature, concentration, collision theory

### Biology
- **Diffusion**: concentration gradient, temperature, particle size
- **Population Growth**: birth/death rate, carrying capacity
- **Membrane Transport**: concentration gradient, ATP, proteins

### Mathematics
- **Quadratic Functions**: coefficients a, b, c, roots, vertex
- **Geometry**: sides, radius, area, perimeter, interior angles
- **Probability**: trials, probability, experimental vs theoretical
- **Statistics**: sample size, mean, std dev, histogram

## Validation Pipeline

```
ScientificValidator
├── _check_parameter_ranges()   // min < max, positive step
├── _check_units()             // Recognized SI units
├── _check_equations()         // Non-empty LaTeX + variables
├── _check_constraints()       // Valid constraint types
├── _validate_physics()        // Domain-specific checks
├── _validate_chemistry()      // Domain-specific checks
├── _validate_biology()        // Domain-specific checks
└── _validate_mathematics()    // Domain-specific checks
```

## Workflow Modes

| Mode | Description | LLM Usage |
|------|-------------|-----------|
| `full_auto` | End-to-end LLM generation | High |
| `template` | Template + LLM tuning | Medium |
| `cached` | Pre-built templates | None |
| `validate_only` | Check existing sim | None |
| `custom` | User-provided spec | Low |

## Performance Targets

- **Render**: 60 FPS via requestAnimationFrame
- **Generation**: < 30 seconds (with LLM), < 5 seconds (templates)
- **HTML Size**: < 100 KB per simulation
- **Memory**: < 50 MB runtime
- **Offline**: Fully self-contained, no external dependencies
