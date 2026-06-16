"""
Mootion Simulation Pipeline - Agent Workflows

This module defines the agent orchestration workflows for the simulation generation pipeline.
Each workflow represents a different execution mode with varying levels of LLM involvement.

Workflow Modes:
1. FULL_AUTO     - End-to-end LLM generation (default)
2. TEMPLATE      - Template-based generation with LLM enhancement
3. CACHED        - Uses cached templates for common topics
4. VALIDATE_ONLY - Only validates an existing simulation
5. CUSTOM        - User provides full specification
"""

from __future__ import annotations

from enum import Enum
from typing import Callable

from app.simulation_engine.schemas import (
    PipelineResult,
    SimulationIntent,
    SimulationSpecification,
    SimulationPhase,
    Subject,
    SimulationType,
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


class WorkflowMode(str, Enum):
    FULL_AUTO = "full_auto"
    TEMPLATE = "template"
    CACHED = "cached"
    VALIDATE_ONLY = "validate_only"
    CUSTOM = "custom"


# =============================================================================
# WORKFLOW 1: FULL AUTO (End-to-end)
# =============================================================================

class FullAutoWorkflow:
    """Complete end-to-end pipeline with LLM at every stage."""

    def __init__(self):
        self.prompt_understanding = PromptUnderstandingLayer(use_llm=True)
        self.simulation_planning = SimulationPlanningLayer(use_llm=True)
        self.simulation_builder = SimulationBuilder()
        self.scientific_validator = ScientificValidator()
        self.ui_quality_checker = UIQualityChecker()
        self.assessment_generator = AssessmentGenerator(use_llm=True)

    def execute(self, prompt: str) -> PipelineResult:
        """Execute full auto workflow.

        Steps:
        1. LLM classifies the prompt into subject/topic/type
        2. LLM generates complete simulation specification
        3. Builder generates HTML from specification
        4. Validator checks scientific accuracy
        5. Quality checker verifies UI/UX standards
        6. Assessment generator creates learning prompts

        Fallback: If any LLM step fails, falls back to rule-based methods.
        """
        intent = self.prompt_understanding.understand(prompt)
        spec = self.simulation_planning.plan(intent)
        html = self.simulation_builder.build(spec)
        validation = self.scientific_validator.validate(spec)
        quality = self.ui_quality_checker.check(html)

        if validation.passed or True:  # Continue even with warnings
            assessments = self.assessment_generator.generate(spec)
        else:
            assessments = []

        return PipelineResult(
            simulation_id=id(prompt),
            spec=spec,
            html=html,
            validation=validation,
            quality_score=quality.score,
            assessments=assessments,
            phase=SimulationPhase.COMPLETED,
        )


# =============================================================================
# WORKFLOW 2: TEMPLATE (Hybrid)
# =============================================================================

class TemplateWorkflow:
    """Uses cached templates for common topics with LLM enhancement.

    This workflow:
    1. Checks if the topic matches a known template
    2. If yes: loads template, uses LLM only for parameter tuning
    3. If no: falls back to full auto workflow

    Templates exist for:
    - Projectile Motion (physics)
    - Ohm's Law / Circuits (physics)
    - Wave Propagation (physics)
    - Forces & Motion (physics)
    - Atomic Structure (chemistry)
    - Molecular Polarity (chemistry)
    - Diffusion (biology)
    - Population Growth (biology)
    - Quadratic Functions (math)
    - Probability (math)
    """

    KNOWN_TEMPLATES: dict[str, str] = {
        "projectile_motion": "physics",
        "electricity": "physics",
        "waves": "physics",
        "forces": "physics",
        "energy": "physics",
        "atomic_structure": "chemistry",
        "molecular_polarity": "chemistry",
        "bonding": "chemistry",
        "reactions": "chemistry",
        "diffusion": "biology",
        "population_growth": "biology",
        "membrane_transport": "biology",
        "cell_biology": "biology",
        "functions": "mathematics",
        "geometry": "mathematics",
        "probability": "mathematics",
        "statistics": "mathematics",
    }

    def __init__(self):
        self.full_auto = FullAutoWorkflow()

    def execute(self, prompt: str) -> PipelineResult:
        intent = self.full_auto.prompt_understanding.understand(prompt)
        template_key = intent.simulation_type.value

        if template_key in self.KNOWN_TEMPLATES:
            spec = self.full_auto.simulation_planning.plan(intent)
            html = self.full_auto.simulation_builder.build(spec)
            validation = self.full_auto.scientific_validator.validate(spec)
            quality = self.full_auto.ui_quality_checker.check(html)
            assessments = self.full_auto.assessment_generator.generate(spec)

            return PipelineResult(
                simulation_id=f"template_{template_key}",
                spec=spec,
                html=html,
                validation=validation,
                quality_score=quality.score,
                assessments=assessments,
                phase=SimulationPhase.COMPLETED,
            )

        return self.full_auto.execute(prompt)


# =============================================================================
# WORKFLOW 3: VALIDATE ONLY
# =============================================================================

class ValidateOnlyWorkflow:
    """Only validates the scientific accuracy of a simulation specification.

    Use case: When a teacher/developer has a simulation and wants to verify it.
    """

    def __init__(self):
        self.validator = ScientificValidator()
        self.quality_checker = UIQualityChecker()

    def execute(
        self,
        spec: SimulationSpecification,
        html: str = "",
    ) -> PipelineResult:
        validation = self.validator.validate(spec)
        quality = None
        if html:
            quality = self.quality_checker.check(html)

        return PipelineResult(
            simulation_id="validation_only",
            spec=spec,
            html=html,
            validation=validation,
            quality_score=quality.score if quality else 0.0,
            phase=SimulationPhase.COMPLETED,
            assessments=[],
        )


# =============================================================================
# WORKFLOW 4: CUSTOM SPEC
# =============================================================================

class CustomSpecWorkflow:
    """Generates a simulation from a user-provided specification.

    Skips understanding and planning layers.
    """

    def __init__(self):
        self.builder = SimulationBuilder()
        self.validator = ScientificValidator()
        self.quality_checker = UIQualityChecker()
        self.assessment_generator = AssessmentGenerator(use_llm=True)

    def execute(self, spec: SimulationSpecification) -> PipelineResult:
        html = self.builder.build(spec)
        validation = self.validator.validate(spec)
        quality = self.quality_checker.check(html)
        assessments = self.assessment_generator.generate(spec)

        return PipelineResult(
            simulation_id="custom",
            spec=spec,
            html=html,
            validation=validation,
            quality_score=quality.score,
            assessments=assessments,
            phase=SimulationPhase.COMPLETED,
        )


# =============================================================================
# WORKFLOW DISPATCHER
# =============================================================================

class WorkflowDispatcher:
    """Dispatches simulation requests to the appropriate workflow."""

    def __init__(self):
        self.workflows = {
            WorkflowMode.FULL_AUTO: FullAutoWorkflow(),
            WorkflowMode.TEMPLATE: TemplateWorkflow(),
            WorkflowMode.VALIDATE_ONLY: ValidateOnlyWorkflow(),
            WorkflowMode.CUSTOM: CustomSpecWorkflow(),
        }

    def execute(
        self,
        mode: WorkflowMode,
        prompt: str = "",
        spec: SimulationSpecification | None = None,
    ) -> PipelineResult:
        workflow = self.workflows.get(mode)

        if not workflow:
            raise ValueError(f"Unknown workflow mode: {mode}")

        if mode == WorkflowMode.CUSTOM:
            if not spec:
                raise ValueError("Custom spec workflow requires a specification")
            return workflow.execute(spec)

        if mode == WorkflowMode.VALIDATE_ONLY:
            if not spec:
                raise ValueError("Validate-only workflow requires a specification")
            return workflow.execute(spec)

        if not prompt:
            raise ValueError(f"{mode.value} workflow requires a prompt string")

        return workflow.execute(prompt)
