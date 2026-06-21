from __future__ import annotations

import time
import uuid

from app.simulation_engine.schemas import (
    PipelineResult,
    SimulationIntent,
    SimulationPhase,
    SimulationSpecification,
    ValidationResult,
)
from app.simulation_engine.prompt_understanding_layer import (
    PromptUnderstandingLayer,
)
from app.simulation_engine.simulation_planning_layer import (
    SimulationPlanningLayer,
)
from app.simulation_engine.simulation_builder import SimulationBuilder
from app.simulation_engine.scientific_validation import ScientificValidator
from app.simulation_engine.ui_quality_layer import UIQualityChecker
from app.simulation_engine.assessment_layer import AssessmentGenerator


class SimulationPipeline:
    def __init__(
        self,
        use_llm: bool = True,
        validate: bool = True,
        quality_check: bool = True,
        generate_assessments: bool = True,
    ):
        self.use_llm = use_llm
        self.validate = validate
        self.quality_check = quality_check
        self.generate_assessments = generate_assessments

        self.prompt_understanding = PromptUnderstandingLayer(use_llm=use_llm)
        self.simulation_planning = SimulationPlanningLayer(use_llm=use_llm)
        self.simulation_builder = SimulationBuilder()
        self.scientific_validator = ScientificValidator()
        self.ui_quality_checker = UIQualityChecker()
        self.assessment_generator = AssessmentGenerator(use_llm=use_llm)

    def run(self, prompt: str, user_grade: str | None = None) -> PipelineResult:
        start_time = time.time()
        result = PipelineResult(
            simulation_id=str(uuid.uuid4()),
            phase=SimulationPhase.PENDING,
        )

        try:
            # Phase 1: Understand the prompt
            result.phase = SimulationPhase.UNDERSTANDING_PROMPT
            intent = self.prompt_understanding.understand(prompt)

            # Phase 2: Plan the simulation
            result.phase = SimulationPhase.PLANNING_SIMULATION
            spec = self.simulation_planning.plan(intent, user_grade=user_grade)
            result.spec = spec

            # Phase 3: Build the simulation HTML
            result.phase = SimulationPhase.BUILDING_SIMULATION
            html = self.simulation_builder.build(spec)
            build_issues = self.simulation_builder.validate_html(html)
            result.html = html
            if build_issues:
                result.error = f"HTML/JS validation failed: {'; '.join(build_issues)}"
                result.phase = SimulationPhase.FAILED
                result.duration_ms = (time.time() - start_time) * 1000
                return result

            # Phase 4: Validate scientific accuracy
            result.phase = SimulationPhase.VALIDATING_SCIENCE
            if self.validate:
                validation = self.scientific_validator.validate(spec)
                result.validation = validation
                if not validation.passed and validation.score < 0.5:
                    result.error = (
                        f"Scientific validation failed: "
                        f"{'; '.join(validation.errors[:3])}"
                    )
                    result.phase = SimulationPhase.FAILED
                    result.duration_ms = (time.time() - start_time) * 1000
                    return result

            # Phase 5: Check UI quality
            result.phase = SimulationPhase.CHECKING_QUALITY
            if self.quality_check:
                quality_result = self.ui_quality_checker.check(html)
                result.quality_score = quality_result.score

            # Phase 6: Generate assessment prompts
            result.phase = SimulationPhase.GENERATING_ASSESSMENTS
            if self.generate_assessments:
                assessments = self.assessment_generator.generate(spec)
                result.assessments = assessments

            result.phase = SimulationPhase.COMPLETED

        except Exception as e:
            result.phase = SimulationPhase.FAILED
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result


class SimulationOrchestrator:
    def __init__(self):
        self.pipeline = SimulationPipeline()
        self.cache: dict[str, PipelineResult] = {}

    async def generate_from_prompt(self, prompt: str, user_grade: str | None = None) -> PipelineResult:
        result = self.pipeline.run(prompt, user_grade=user_grade)
        self.cache[result.simulation_id] = result
        return result

    async def generate_from_spec(
        self, spec: SimulationSpecification
    ) -> PipelineResult:
        start_time = time.time()
        result = PipelineResult(
            simulation_id=str(uuid.uuid4()),
            phase=SimulationPhase.BUILDING_SIMULATION,
            spec=spec,
        )

        try:
            html = self.pipeline.simulation_builder.build(spec)
            result.html = html

            build_issues = self.pipeline.simulation_builder.validate_html(html)
            if build_issues:
                result.error = f"HTML/JS validation failed: {'; '.join(build_issues)}"
                result.phase = SimulationPhase.FAILED
                result.duration_ms = (time.time() - start_time) * 1000
                return result

            if self.pipeline.validate:
                validation = self.pipeline.scientific_validator.validate(spec)
                result.validation = validation

            if self.pipeline.quality_check:
                quality = self.pipeline.ui_quality_checker.check(html)
                result.quality_score = quality.score

            if self.pipeline.generate_assessments:
                assessments = self.pipeline.assessment_generator.generate(spec)
                result.assessments = assessments

            result.phase = SimulationPhase.COMPLETED
        except Exception as e:
            result.phase = SimulationPhase.FAILED
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        self.cache[result.simulation_id] = result
        return result

    def get_result(self, simulation_id: str) -> PipelineResult | None:
        return self.cache.get(simulation_id)

    def get_supported_subjects(self) -> list[dict]:
        return [
            {
                "id": "physics",
                "name": "Physics",
                "topics": [
                    "kinematics", "projectile_motion", "forces", "energy",
                    "electricity", "waves",
                ],
                "icon": "atom",
            },
            {
                "id": "chemistry",
                "name": "Chemistry",
                "topics": [
                    "atomic_structure", "molecular_polarity", "bonding",
                    "reactions", "equilibrium",
                ],
                "icon": "flask",
            },
            {
                "id": "biology",
                "name": "Biology",
                "topics": [
                    "membrane_transport", "diffusion", "genetics",
                    "population_growth", "cell_biology",
                ],
                "icon": "dna",
            },
            {
                "id": "mathematics",
                "name": "Mathematics",
                "topics": [
                    "functions", "geometry", "probability", "statistics",
                ],
                "icon": "sigma",
            },
        ]

    def get_example_prompts(self) -> list[str]:
        return [
            "Explain projectile motion",
            "Show me membrane transport",
            "Teach me electric fields",
            "Explain molecular polarity",
            "Show diffusion of particles",
            "Demonstrate Ohm's law",
            "Teach me quadratic functions",
            "Show population growth model",
            "Explain atomic structure",
            "Demonstrate chemical reactions",
        ]
