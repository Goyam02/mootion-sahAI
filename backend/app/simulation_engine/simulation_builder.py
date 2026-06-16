from __future__ import annotations

import uuid

from app.simulation_engine.schemas import (
    SimulationSpecification,
    Subject,
)
from app.simulation_engine.templates import (
    build_physics_simulation,
    build_chemistry_simulation,
    build_biology_simulation,
    build_math_simulation,
    build_simulation_html,
)


class SimulationBuilder:
    def build(self, spec: SimulationSpecification) -> str:
        subject = spec.subject

        if subject == Subject.PHYSICS:
            return build_physics_simulation(spec)
        elif subject == Subject.CHEMISTRY:
            return build_chemistry_simulation(spec)
        elif subject == Subject.BIOLOGY:
            return build_biology_simulation(spec)
        elif subject == Subject.MATHEMATICS:
            return build_math_simulation(spec)
        else:
            return build_simulation_html(spec)

    def validate_html(self, html: str) -> list[str]:
        issues = []
        required_checks = [
            ("StateManager", "Missing StateManager class"),
            ("SimulationEngine", "Missing SimulationEngine class"),
            ("Renderer", "Missing Renderer class"),
            ("ControlsManager", "Missing ControlsManager class"),
            ("EventBus", "Missing EventBus class"),
            ("requestAnimationFrame", "Missing requestAnimationFrame loop"),
            ('id="canvas"', "Missing simulation canvas"),
            ('id="play-btn"', "Missing play/pause button"),
            ('id="reset-btn"', "Missing reset button"),
            ("class=\"ctrl\"", "Missing control sliders section"),
        ]

        for pattern, message in required_checks:
            if pattern not in html:
                issues.append(message)

        return issues
