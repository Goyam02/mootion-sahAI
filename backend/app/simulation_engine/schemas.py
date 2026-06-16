from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Subject(str, Enum):
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    MATHEMATICS = "mathematics"


class SimulationType(str, Enum):
    KINEMATICS = "kinematics"
    PROJECTILE_MOTION = "projectile_motion"
    FORCES = "forces"
    ENERGY = "energy"
    ELECTRICITY = "electricity"
    WAVES = "waves"
    ATOMIC_STRUCTURE = "atomic_structure"
    MOLECULAR_POLARITY = "molecular_polarity"
    BONDING = "bonding"
    REACTIONS = "reactions"
    EQUILIBRIUM = "equilibrium"
    MEMBRANE_TRANSPORT = "membrane_transport"
    DIFFUSION = "diffusion"
    GENETICS = "genetics"
    POPULATION_GROWTH = "population_growth"
    CELL_BIOLOGY = "cell_biology"
    BUOYANCY = "buoyancy"
    FUNCTIONS = "functions"
    GEOMETRY = "geometry"
    PROBABILITY = "probability"
    STATISTICS = "statistics"
    CUSTOM = "custom"


class SimulationPhase(str, Enum):
    PENDING = "pending"
    UNDERSTANDING_PROMPT = "understanding_prompt"
    PLANNING_SIMULATION = "planning_simulation"
    BUILDING_SIMULATION = "building_simulation"
    VALIDATING_SCIENCE = "validating_science"
    CHECKING_QUALITY = "checking_quality"
    GENERATING_ASSESSMENTS = "generating_assessments"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationIntent(BaseModel):
    subject: Subject
    topic: str
    concepts: list[str] = Field(default_factory=list)
    simulation_type: SimulationType
    grade_level: str = "high_school"
    confidence: float = 0.0
    raw_prompt: str = ""


class SimulationEntity(BaseModel):
    id: str
    name: str
    type: str
    initial_state: dict[str, Any] = Field(default_factory=dict)
    properties: list[str] = Field(default_factory=list)


class SimulationParameter(BaseModel):
    id: str
    name: str
    symbol: str
    type: str = "number"
    default: float = 0.0
    min: float = 0.0
    max: float = 100.0
    step: float = 1.0
    unit: str = ""
    description: str = ""


class SimulationEquation(BaseModel):
    id: str
    latex: str
    description: str
    variables: dict[str, str] = Field(default_factory=dict)


class SimulationConstraint(BaseModel):
    type: str
    description: str
    rule: str


class SimulationVisualization(BaseModel):
    type: str
    target: str
    style: dict[str, Any] = Field(default_factory=dict)


class SimulationGraph(BaseModel):
    id: str
    title: str
    x_axis: str
    y_axis: str
    x_label: str = ""
    y_label: str = ""
    data_type: str = "live"
    series: list[dict[str, Any]] = Field(default_factory=list)


class AssessmentPrompt(BaseModel):
    id: str
    type: str
    question: str
    hint: str = ""
    difficulty: str = "medium"
    learning_goal: str = ""


class SimulationSpecification(BaseModel):
    subject: Subject
    topic: str
    simulation_type: SimulationType
    title: str
    learning_objectives: list[str] = Field(default_factory=list)
    entities: list[SimulationEntity] = Field(default_factory=list)
    parameters: list[SimulationParameter] = Field(default_factory=list)
    equations: list[SimulationEquation] = Field(default_factory=list)
    constraints: list[SimulationConstraint] = Field(default_factory=list)
    visualizations: list[SimulationVisualization] = Field(default_factory=list)
    graphs: list[SimulationGraph] = Field(default_factory=list)
    assessment_prompts: list[AssessmentPrompt] = Field(default_factory=list)
    canvas_width: int = 600
    canvas_height: int = 400
    background_color: str = "#0f172a"
    grid_enabled: bool = True
    interaction_mode: str = "direct"
    grade_level: str = "high_school"
    duration_minutes: int = 10
    raw_spec: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    passed: bool = False
    score: float = 0.0
    checks: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    simulation_id: str
    spec: SimulationSpecification | None = None
    html: str = ""
    validation: ValidationResult | None = None
    quality_score: float = 0.0
    assessments: list[AssessmentPrompt] = Field(default_factory=list)
    phase: SimulationPhase = SimulationPhase.PENDING
    error: str | None = None
    duration_ms: float = 0.0
