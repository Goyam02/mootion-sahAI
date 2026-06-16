import json
import unittest
from typing import Any

from app.simulation_engine.schemas import (
    AssessmentPrompt,
    SimulationConstraint,
    SimulationEntity,
    SimulationEquation,
    SimulationGraph,
    SimulationParameter,
    SimulationSpecification,
    SimulationType,
    Subject,
    ValidationResult,
)
from app.simulation_engine.pipeline import SimulationPipeline
from app.simulation_engine.prompt_understanding_layer import (
    PromptUnderstandingLayer,
)
from app.simulation_engine.scientific_validation import ScientificValidator
from app.simulation_engine.ui_quality_layer import UIQualityChecker
from app.simulation_engine.assessment_layer import AssessmentGenerator
from app.simulation_engine.simulation_builder import SimulationBuilder


class TestSimulationPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = SimulationPipeline(
            use_llm=False,
            validate=True,
            quality_check=True,
            generate_assessments=True,
        )

    def test_pipeline_runs_end_to_end(self):
        result = self.pipeline.run("Explain projectile motion")
        self.assertEqual(result.phase.value, "completed")
        self.assertIsNone(result.error)
        self.assertGreater(len(result.html), 0, "Should produce HTML")
        self.assertIsNotNone(result.spec)
        self.assertEqual(result.spec.subject, Subject.PHYSICS)

    def test_pipeline_produces_valid_html(self):
        result = self.pipeline.run("Explain Ohm's law")
        required = [
            "StateManager", "SimulationEngine", "Renderer",
            "ControlsManager", "EventBus", "requestAnimationFrame",
            'id="canvas"', 'id="play-btn"', 'id="reset-btn"',
            "class=\"ctrl\"", "class=\"vcard\"",
        ]
        for r in required:
            self.assertIn(r, result.html, f"Missing required element: {r}")
        self.assertNotIn("__SPEC__", result.html, "SPEC placeholder should be replaced")
        self.assertNotIn("__SCRIPT__", result.html, "SCRIPT placeholder should be replaced")

    def test_pipeline_with_different_subjects(self):
        prompt_map = [
            ("Explain diffusion", Subject.BIOLOGY),
            ("Show atomic structure", Subject.CHEMISTRY),
            ("Teach me quadratic functions", Subject.MATHEMATICS),
            ("Demonstrate forces and motion", Subject.PHYSICS),
        ]
        for prompt, expected_subject in prompt_map:
            result = self.pipeline.run(prompt)
            self.assertEqual(result.phase.value, "completed", f"Failed for: {prompt}")
            self.assertEqual(result.spec.subject, expected_subject, f"Wrong subject for: {prompt}")

    def test_pipeline_handles_nonsense_prompt_gracefully(self):
        result = self.pipeline.run("")
        self.assertEqual(result.phase.value, "completed")
        self.assertGreater(len(result.html), 0)

    def test_pipeline_handles_short_prompt(self):
        result = self.pipeline.run("waves")
        self.assertEqual(result.phase.value, "completed")
        self.assertIn("wave", result.html.lower())


class TestPromptUnderstanding(unittest.TestCase):
    def setUp(self):
        self.layer = PromptUnderstandingLayer(use_llm=False)

    def test_classify_physics(self):
        result = self.layer.understand("Explain projectile motion with velocity and angle")
        self.assertEqual(result.subject, Subject.PHYSICS)
        self.assertIn("projectile", result.concepts)

    def test_classify_chemistry(self):
        result = self.layer.understand("Show atomic structure and bonding")
        self.assertEqual(result.subject, Subject.CHEMISTRY)
        self.assertIn("atomic", result.concepts)

    def test_classify_biology(self):
        result = self.layer.understand("Teach me about cell membrane transport")
        self.assertEqual(result.subject, Subject.BIOLOGY)

    def test_classify_mathematics(self):
        result = self.layer.understand("Demonstrate probability and statistics")
        self.assertEqual(result.subject, Subject.MATHEMATICS)

    def test_simulation_type_detection(self):
        cases = [
            ("projectile motion", SimulationType.PROJECTILE_MOTION),
            ("electric circuit", SimulationType.ELECTRICITY),
            ("wave propagation", SimulationType.WAVES),
            ("population growth", SimulationType.POPULATION_GROWTH),
            ("diffusion process", SimulationType.DIFFUSION),
        ]
        for prompt, expected_type in cases:
            result = self.layer.understand(prompt)
            self.assertEqual(result.simulation_type, expected_type, f"Failed for: {prompt}")

    def test_grade_level_estimation(self):
        basic = self.layer.understand("What is gravity, for kids")
        self.assertEqual(basic.grade_level, "middle_school")
        advanced = self.layer.understand("quantum mechanics and lagrangian")
        self.assertEqual(advanced.grade_level, "advanced")


class TestScientificValidation(unittest.TestCase):
    def setUp(self):
        self.validator = ScientificValidator()
        self.base_spec = SimulationSpecification(
            subject=Subject.PHYSICS,
            topic="Projectile Motion",
            simulation_type=SimulationType.PROJECTILE_MOTION,
            title="Test",
            learning_objectives=["Test objective"],
            parameters=[
                SimulationParameter(
                    id="angle", name="Angle", symbol="theta",
                    min=0, max=90, default=45, step=1,
                    unit="deg", description="Launch angle",
                ),
                SimulationParameter(
                    id="velocity", name="Velocity", symbol="v",
                    min=0, max=50, default=20, step=1,
                    unit="m/s", description="Initial velocity",
                ),
                SimulationParameter(
                    id="gravity", name="Gravity", symbol="g",
                    min=1, max=20, default=9.81, step=0.1,
                    unit="m/s^2", description="Gravity",
                ),
            ],
        )

    def test_valid_spec_passes(self):
        result = self.validator.validate(self.base_spec)
        self.assertTrue(result.passed)

    def test_invalid_parameter_range_fails(self):
        spec = self.base_spec.copy(deep=True)
        spec.parameters[0].min = 50
        spec.parameters[0].max = 10
        result = self.validator.validate(spec)
        self.assertFalse(result.passed)
        self.assertGreater(len(result.errors), 0)

    def test_negative_kelvin_fails(self):
        spec = SimulationSpecification(
            subject=Subject.CHEMISTRY,
            topic="Temperature",
            simulation_type=SimulationType.REACTIONS,
            title="Test",
            parameters=[
                SimulationParameter(
                    id="temp", name="Temperature", symbol="T",
                    min=-10, max=100, default=25, step=1,
                    unit="K", description="Temperature",
                ),
            ],
        )
        result = self.validator.validate(spec)
        self.assertFalse(result.passed)
        has_negative_error = any("negative" in e.lower() for e in result.errors)
        self.assertTrue(has_negative_error)

    def test_biology_population_validation(self):
        spec = SimulationSpecification(
            subject=Subject.BIOLOGY,
            topic="Population",
            simulation_type=SimulationType.POPULATION_GROWTH,
            title="Test",
            parameters=[
                SimulationParameter(
                    id="birth", name="Birth Rate", symbol="b",
                    min=0, max=1, default=0.5, step=0.1,
                    unit="", description="Birth rate",
                ),
            ],
        )
        result = self.validator.validate(spec)
        # Should pass but with warnings
        self.assertTrue(result.passed)
        warning_texts = [w.lower() for w in result.warnings]
        has_death_warning = any("death" in w for w in warning_texts)
        has_carrying_warning = any("carrying" in w for w in warning_texts)
        self.assertTrue(has_death_warning or has_carrying_warning)


class TestSimulationBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = SimulationBuilder()

    def _make_spec(self, subject: Subject, sim_type: SimulationType, topic: str = "Test") -> SimulationSpecification:
        return SimulationSpecification(
            subject=subject,
            topic=topic,
            simulation_type=sim_type,
            title=f"{topic} Simulation",
            learning_objectives=[f"Learn about {topic}"],
            parameters=[
                SimulationParameter(
                    id="param_1", name="Parameter 1", symbol="p1",
                    min=0, max=100, default=50, step=1,
                    unit="", description="Test param",
                ),
            ],
        )

    def test_build_physics_produces_html(self):
        spec = self._make_spec(Subject.PHYSICS, SimulationType.PROJECTILE_MOTION)
        html = self.builder.build(spec)
        self.assertIn("SimulationEngine", html)
        self.assertGreater(len(html), 1000)

    def test_build_chemistry_produces_html(self):
        spec = self._make_spec(Subject.CHEMISTRY, SimulationType.ATOMIC_STRUCTURE)
        html = self.builder.build(spec)
        self.assertIn("SimulationEngine", html)

    def test_build_biology_produces_html(self):
        spec = self._make_spec(Subject.BIOLOGY, SimulationType.DIFFUSION)
        html = self.builder.build(spec)
        self.assertIn("SimulationEngine", html)

    def test_build_math_produces_html(self):
        spec = self._make_spec(Subject.MATHEMATICS, SimulationType.FUNCTIONS)
        html = self.builder.build(spec)
        self.assertIn("SimulationEngine", html)

    def test_physics_types_all_produce_html(self):
        types = [
            SimulationType.PROJECTILE_MOTION,
            SimulationType.ELECTRICITY,
            SimulationType.WAVES,
            SimulationType.FORCES,
            SimulationType.ENERGY,
        ]
        for sim_type in types:
            spec = self._make_spec(Subject.PHYSICS, sim_type, sim_type.value)
            html = self.builder.build(spec)
            self.assertGreater(len(html), 500, f"Failed for {sim_type}")

    def test_validate_html_checks_required_elements(self):
        spec = self._make_spec(Subject.PHYSICS, SimulationType.PROJECTILE_MOTION)
        html = self.builder.build(spec)
        issues = self.builder.validate_html(html)
        self.assertEqual(len(issues), 0, f"Validation issues: {issues}")


class TestAssessmentGeneration(unittest.TestCase):
    def setUp(self):
        self.generator = AssessmentGenerator(use_llm=False)

    def test_generates_assessments_for_known_type(self):
        spec = SimulationSpecification(
            subject=Subject.PHYSICS,
            topic="Projectile Motion",
            simulation_type=SimulationType.PROJECTILE_MOTION,
            title="Test",
        )
        assessments = self.generator.generate(spec)
        self.assertGreaterEqual(len(assessments), 2)
        for ap in assessments:
            self.assertIsInstance(ap, AssessmentPrompt)
            self.assertTrue(len(ap.question) > 0)
            self.assertIn(ap.type, ["prediction", "inquiry", "experimentation", "reflection"])

    def test_generates_assessments_for_unknown_type(self):
        spec = SimulationSpecification(
            subject=Subject.PHYSICS,
            topic="Custom Topic",
            simulation_type=SimulationType.CUSTOM,
            title="Test",
        )
        assessments = self.generator.generate(spec)
        self.assertGreaterEqual(len(assessments), 2)

    def test_uses_existing_assessments(self):
        existing = [
            AssessmentPrompt(id="ap_1", type="prediction", question="Q1?", hint="H1"),
            AssessmentPrompt(id="ap_2", type="inquiry", question="Q2?", hint="H2"),
        ]
        spec = SimulationSpecification(
            subject=Subject.PHYSICS,
            topic="Test",
            simulation_type=SimulationType.PROJECTILE_MOTION,
            title="Test",
            assessment_prompts=existing,
        )
        assessments = self.generator.generate(spec)
        self.assertEqual(len(assessments), 2)
        self.assertEqual(assessments[0].question, "Q1?")
        self.assertEqual(assessments[1].question, "Q2?")


class TestUIQualityChecker(unittest.TestCase):
    def setUp(self):
        self.checker = UIQualityChecker()
        self.pipeline = SimulationPipeline(
            use_llm=False, validate=False, quality_check=False,
        )

    def test_generated_html_passes_quality_checks(self):
        result = self.pipeline.run("Explain projectile motion")
        quality = self.checker.check(result.html)
        self.assertTrue(
            quality.passed,
            f"Quality check failed: errors={quality.errors}, warnings={quality.warnings}",
        )

    def test_missing_canvas_fails(self):
        result = self.checker.check("<html><body></body></html>")
        self.assertFalse(result.passed)
        canvas_errors = [e for e in result.errors if "canvas" in e.lower()]
        self.assertGreater(len(canvas_errors), 0)

    def test_missing_reset_fails(self):
        html = """<html><head><meta name="viewport" content="width=device-width"></head>
<body><canvas id="canvas"></canvas><input type="range"><div class="vcard"></div></body></html>"""
        result = self.checker.check(html)
        reset_errors = [e for e in result.errors if "reset" in e.lower()]
        self.assertGreater(len(reset_errors), 0)


class TestSimulationOrchestrator(unittest.TestCase):
    def setUp(self):
        from app.simulation_engine.pipeline import SimulationOrchestrator
        self.orchestrator = SimulationOrchestrator()

    def test_generate_from_prompt(self):
        import asyncio
        result = asyncio.run(self.orchestrator.generate_from_prompt("Explain projectile motion"))
        self.assertEqual(result.phase.value, "completed")
        self.assertIsNotNone(self.orchestrator.get_result(result.simulation_id))

    def test_generate_from_spec(self):
        import asyncio
        spec = SimulationSpecification(
            subject=Subject.PHYSICS,
            topic="Projectile Motion",
            simulation_type=SimulationType.PROJECTILE_MOTION,
            title="Test",
            parameters=[
                SimulationParameter(
                    id="angle", name="Angle", symbol="theta",
                    min=0, max=90, default=45, step=1,
                    unit="deg", description="Launch angle",
                ),
            ],
        )
        result = asyncio.run(self.orchestrator.generate_from_spec(spec))
        self.assertEqual(result.phase.value, "completed")
        self.assertGreater(len(result.html), 0)

    def test_supported_subjects(self):
        subjects = self.orchestrator.get_supported_subjects()
        self.assertEqual(len(subjects), 4)
        subject_ids = [s["id"] for s in subjects]
        self.assertIn("physics", subject_ids)
        self.assertIn("chemistry", subject_ids)
        self.assertIn("biology", subject_ids)
        self.assertIn("mathematics", subject_ids)

    def test_example_prompts(self):
        prompts = self.orchestrator.get_example_prompts()
        self.assertGreater(len(prompts), 5)
        self.assertIn("Explain projectile motion", prompts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
