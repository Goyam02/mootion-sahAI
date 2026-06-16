from app.simulation_engine.templates.base_template import build_simulation_html
from app.simulation_engine.templates.physics_templates import build_physics_simulation
from app.simulation_engine.templates.chemistry_templates import build_chemistry_simulation
from app.simulation_engine.templates.biology_templates import build_biology_simulation
from app.simulation_engine.templates.math_templates import build_math_simulation

__all__ = [
    "build_simulation_html",
    "build_physics_simulation",
    "build_chemistry_simulation",
    "build_biology_simulation",
    "build_math_simulation",
]
