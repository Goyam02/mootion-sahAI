from __future__ import annotations

import json
import uuid

from app.simulation_engine.prompt_understanding_layer import query_llm
from app.simulation_engine.schemas import (
    AssessmentPrompt,
    SimulationConstraint,
    SimulationEntity,
    SimulationEquation,
    SimulationGraph,
    SimulationIntent,
    SimulationParameter,
    SimulationSpecification,
    SimulationVisualization,
)


SUBJECT_PROMPTS: dict[str, str] = {
    "physics": """You are a physics education simulation designer.
Design an interactive HTML5 Canvas simulation that teaches physics concepts through experimentation.
Include:
- Realistic physics equations with correct units
- Interactive parameter controls (sliders) for independent variables
- Live readouts showing calculated values
- Real-time graphs of relationships between variables
- Visual animations that accurately represent the physics
- Reset functionality
- Play/Pause controls""",

    "chemistry": """You are a chemistry education simulation designer.
Design an interactive HTML5 Canvas simulation that teaches chemistry concepts through visualization.
Include:
- Accurate chemical representations
- Interactive parameter controls
- Dynamic visualizations of molecular/atomic behavior
- Real-time data displays
- Reset and animation controls
- Scientific accuracy in all representations""",

    "biology": """You are a biology education simulation designer.
Design an interactive HTML5 Canvas simulation that teaches biology concepts through dynamic systems modeling.
Include:
- Accurate biological representations
- Process visualization (diffusion, transport, division, etc.)
- Interactive parameter controls
- Real-time counters and measurements
- System state visualization
- Reset and speed controls""",

    "mathematics": """You are a mathematics education simulation designer.
Design an interactive HTML5 Canvas simulation that teaches mathematical concepts through visual exploration.
Include:
- Interactive function/geometry plotting
- Parameter sliders to explore transformations
- Live coordinate readouts
- Interactive graph manipulation
- Grid display
- Reset functionality""",
}


SIMULATION_TYPE_HINTS: dict[str, str] = {
    "projectile_motion": "Visualize a projectile with adjustable angle, initial velocity, mass, and gravity. Show trajectory path, height, range, time of flight, and velocity components. Include real-time position tracking and energy bar.",
    "kinematics": "Show motion with adjustable acceleration, initial velocity, and time. Include position-time, velocity-time, and acceleration-time graphs. Animate a moving object.",
    "forces": "Show forces acting on objects with adjustable mass, applied force, friction, and angle. Include free body diagram, net force calculation, and acceleration readout.",
    "energy": "Show energy transformations with adjustable parameters. Include kinetic, potential, and total energy bars. Animate a system showing energy conversion.",
    "electricity": "Show a circuit with adjustable voltage, resistance, and components. Include current readout, power calculation, and animated charge flow. Show Ohm's law relationship.",
    "waves": "Show wave propagation with adjustable amplitude, frequency, wavelength, and speed. Include wave visualization, phase indicator, and superposition demonstration.",
    "atomic_structure": "Show atomic model with adjustable proton/neutron/electron counts. Include orbital visualization, element identification, and charge balance display.",
    "molecular_polarity": "Show molecular geometry with adjustable atoms and bond types. Include electronegativity visualization, dipole moment vector, and polarity indicator.",
    "bonding": "Show ionic/covalent bonding with adjustable atoms. Include electron transfer/sharing visualization, bond energy display, and resulting compound formula.",
    "reactions": "Show chemical reaction with adjustable reactant concentrations and temperature. Include molecular collision visualization, reaction rate display, and product formation.",
    "equilibrium": "Show reversible reaction with adjustable concentrations and temperature. Include forward/backward rate display, equilibrium constant calculation, and concentration-time graph.",
    "membrane_transport": "Show cell membrane with adjustable concentration gradient and transport proteins. Include particle movement visualization, transport rate display, and ATP usage counter.",
    "diffusion": "Show particle diffusion with adjustable concentration, temperature, and particle size. Include concentration gradient visualization, diffusion rate display, and Fick's law readout.",
    "genetics": "Show Punnett square with adjustable parent genotypes. Include allele combination visualization, phenotype ratio display, and probability calculations.",
    "population_growth": "Show population dynamics with adjustable birth rate, death rate, and carrying capacity. Include population-time graph, logistic/exponential growth comparison.",
    "cell_biology": "Show cell structure with adjustable zoom and labeled organelles. Include interactive exploration of cell components with descriptions.",
    "buoyancy": "Show a fluid container with a submerged/floating object. Include adjustable mass, volume, fluid density, gravity. Visualize buoyant force, weight, net force, and object position. Show Archimedes' principle with displaced fluid visualization.",
    "functions": "Show interactive function plotting with adjustable coefficients. Include multiple function comparison, derivative visualization, and root finding.",
    "geometry": "Show geometric constructions with adjustable parameters. Include angle measurement, area/perimeter calculation, and interactive manipulation.",
    "probability": "Show probability experiments with adjustable trials and outcomes. Include frequency distribution, theoretical vs experimental probability comparison.",
    "statistics": "Show statistical data visualization with adjustable sample size and distribution parameters. Include mean/median/mode display, histogram, and box plot.",
}


class SimulationPlanningLayer:
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm

    def plan(self, intent: SimulationIntent) -> SimulationSpecification:
        if self.use_llm:
            try:
                return self._llm_generate_spec(intent)
            except Exception as e:
                pass

        return self._rule_based_spec(intent)

    def _llm_generate_spec(self, intent: SimulationIntent) -> SimulationSpecification:
        subject_hint = SUBJECT_PROMPTS.get(intent.subject.value, "")
        type_hint = SIMULATION_TYPE_HINTS.get(
            intent.simulation_type.value, ""
        )
        concepts_str = ", ".join(intent.concepts)

        llm_prompt = f"""{subject_hint}

Simulation Type: {intent.simulation_type.value}
Topic: {intent.topic}
Concepts: {concepts_str}
Grade Level: {intent.grade_level}

{type_hint}

Generate a complete simulation specification as JSON.

Return ONLY valid JSON with this exact structure:
{{
  "subject": "{intent.subject.value}",
  "topic": "{intent.topic}",
  "simulation_type": "{intent.simulation_type.value}",
  "title": "engaging simulation title",
  "learning_objectives": ["objective 1", "objective 2", "objective 3"],
  "entities": [
    {{
      "id": "unique_id",
      "name": "display name",
      "type": "object|particle|field|graph|circuit|molecule|cell|organism",
      "initial_state": {{}},
      "properties": ["property1", "property2"]
    }}
  ],
  "parameters": [
    {{
      "id": "param_id",
      "name": "Display Name",
      "symbol": "symbol",
      "type": "number",
      "default": 0.0,
      "min": 0.0,
      "max": 100.0,
      "step": 1.0,
      "unit": "unit",
      "description": "what this parameter controls"
    }}
  ],
  "equations": [
    {{
      "id": "eq_id",
      "latex": "LaTeX equation string",
      "description": "what this equation describes",
      "variables": {{"var": "description"}}
    }}
  ],
  "constraints": [
    {{
      "type": "physical|chemical|mathematical|biological",
      "description": "constraint description",
      "rule": "specific rule"
    }}
  ],
  "visualizations": [
    {{
      "type": "canvas_animation|bar_chart|energy_bar|force_arrow|trajectory|field_line|particle_system|molecular_model",
      "target": "what to visualize",
      "style": {{"color": "#hex", "opacity": 0.8}}
    }}
  ],
  "graphs": [
    {{
      "id": "graph_id",
      "title": "Graph Title",
      "x_axis": "variable",
      "y_axis": "variable",
      "x_label": "X Axis Label (unit)",
      "y_label": "Y Axis Label (unit)",
      "data_type": "live|history|static",
      "series": [{{"name": "Series 1", "color": "#hex", "style": "line|scatter"}}]
    }}
  ],
  "assessment_prompts": [
    {{
      "id": "ap_1",
      "type": "prediction|inquiry|experimentation|reflection",
      "question": "thought-provoking question about the simulation",
      "hint": "helpful hint",
      "difficulty": "easy|medium|hard",
      "learning_goal": "what this question teaches"
    }}
  ],
  "canvas_width": 600,
  "canvas_height": 400,
  "background_color": "#0f172a",
  "grid_enabled": true,
  "interaction_mode": "direct",
  "duration_minutes": 10
}}

Guidelines:
- Parameters should have realistic min/max ranges for the topic
- Equations must be scientifically accurate
- Learning objectives must be measurable
- Assessment prompts should encourage prediction before experimentation
- Include 3-5 parameters, 1-3 equations, 2-4 assessment prompts
- For graphs, use 'live' for real-time plotting, 'history' for tracking over time
- Entities should represent all visible/interactive elements

Return ONLY the JSON object. No markdown, no explanation."""

        response = query_llm(llm_prompt, temperature=0.3)
        response = self._clean_json_response(response)

        try:
            data = json.loads(response)
            data["simulation_id"] = str(uuid.uuid4())
            return SimulationSpecification(**data)
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Failed to parse LLM spec: {e}")

    def _rule_based_spec(self, intent: SimulationIntent) -> SimulationSpecification:
        return SimulationSpecification(
            subject=intent.subject,
            topic=intent.topic,
            simulation_type=intent.simulation_type,
            title=f"{intent.topic} - Interactive Simulation",
            learning_objectives=[
                f"Understand the key principles of {intent.topic}",
                f"Explore how changing parameters affects {intent.topic}",
                f"Predict outcomes based on scientific understanding of {intent.topic}",
            ],
            entities=[
                SimulationEntity(
                    id="main_object",
                    name=intent.topic,
                    type="object",
                    initial_state={"x": 100, "y": 300},
                    properties=["position", "velocity", "acceleration"],
                )
            ],
            parameters=[
                SimulationParameter(
                    id="param_1",
                    name="Parameter 1",
                    symbol="p1",
                    type="number",
                    default=50.0,
                    min=0.0,
                    max=100.0,
                    step=1.0,
                    unit="",
                    description="Primary control parameter",
                )
            ],
            equations=[
                SimulationEquation(
                    id="eq_1",
                    latex="y = f(x)",
                    description="Primary relationship",
                    variables={"x": "input", "y": "output"},
                )
            ],
            constraints=[
                SimulationConstraint(
                    type="physical",
                    description="Values must stay within realistic ranges",
                    rule="All parameters clamped to [min, max]",
                )
            ],
            visualizations=[
                SimulationVisualization(
                    type="canvas_animation",
                    target="main_object",
                    style={"color": "#8b5cf6", "opacity": 0.9},
                )
            ],
            graphs=[
                SimulationGraph(
                    id="graph_1",
                    title="Relationship",
                    x_axis="param_1",
                    y_axis="output",
                    x_label="Parameter",
                    y_label="Output",
                    data_type="live",
                    series=[{"name": "Value", "color": "#06b6d4", "style": "line"}],
                )
            ],
            assessment_prompts=[
                AssessmentPrompt(
                    id="ap_1",
                    type="prediction",
                    question=f"What do you predict will happen when you increase the parameter?",
                    hint="Think about the relationship between variables.",
                    difficulty="medium",
                    learning_goal="Develop predictive thinking about {intent.topic}",
                )
            ],
            canvas_width=600,
            canvas_height=400,
            background_color="#0f172a",
            grid_enabled=True,
            interaction_mode="direct",
            grade_level=intent.grade_level,
            duration_minutes=10,
        )

    def _clean_json_response(self, response: str) -> str:
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()
