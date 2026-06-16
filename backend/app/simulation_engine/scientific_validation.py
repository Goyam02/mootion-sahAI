from __future__ import annotations

import math
import re

from app.simulation_engine.schemas import (
    SimulationSpecification,
    Subject,
    ValidationResult,
)


PHYSICS_CONSTANTS = {
    "g": 9.81,
    "G": 6.674e-11,
    "c": 299792458,
    "h": 6.626e-34,
    "k": 1.381e-23,
    "e": 1.602e-19,
    "epsilon_0": 8.854e-12,
    "mu_0": 4e-7 * math.pi,
}

CHEMISTRY_CONSTANTS = {
    "R": 8.314,
    "N_A": 6.022e23,
    "F": 96485,
    "k_B": 1.381e-23,
}

VALID_UNITS = {
    "m", "s", "kg", "N", "J", "W", "V", "A", "Ohm", "F", "T",
    "Hz", "Pa", "atm", "mol", "K", "C", "eV", "L", "g", "m/s",
    "m/s^2", "N/kg", "J/kg", "W/m^2", "V/m", "A/m", "Ohm*m",
    "pH", "M", "mM", "uM", "nM",
}


class ScientificValidator:
    def validate(self, spec: SimulationSpecification) -> ValidationResult:
        result = ValidationResult(passed=True, score=1.0)

        self._check_parameter_ranges(spec, result)
        self._check_units(spec, result)
        self._check_equations(spec, result)
        self._check_constraints(spec, result)

        if spec.subject == Subject.PHYSICS:
            self._validate_physics(spec, result)
        elif spec.subject == Subject.CHEMISTRY:
            self._validate_chemistry(spec, result)
        elif spec.subject == Subject.BIOLOGY:
            self._validate_biology(spec, result)
        elif spec.subject == Subject.MATHEMATICS:
            self._validate_mathematics(spec, result)

        total_checks = len(result.checks)
        total_errors = len(result.errors)
        total_warnings = len(result.warnings)

        if total_checks > 0:
            result.score = max(0.0, 1.0 - (total_errors * 0.3 + total_warnings * 0.1))
        result.passed = total_errors == 0 and result.score >= 0.7

        return result

    def _check_parameter_ranges(self, spec: SimulationSpecification, result: ValidationResult) -> None:
        for param in spec.parameters:
            if param.min >= param.max:
                result.errors.append(
                    f"Parameter '{param.name}': min ({param.min}) >= max ({param.max})"
                )
                result.checks.append({
                    "check": "parameter_range",
                    "status": "fail",
                    "detail": f"{param.name}: invalid range",
                })
            else:
                result.checks.append({
                    "check": "parameter_range",
                    "status": "pass",
                    "detail": f"{param.name}: [{param.min}, {param.max}] valid",
                })

            if param.step <= 0:
                result.warnings.append(
                    f"Parameter '{param.name}': step ({param.step}) should be positive"
                )

            if param.default < param.min or param.default > param.max:
                result.warnings.append(
                    f"Parameter '{param.name}': default ({param.default}) outside range"
                )

    def _check_units(self, spec: SimulationSpecification, result: ValidationResult) -> None:
        for param in spec.parameters:
            if param.unit and param.unit not in VALID_UNITS:
                result.warnings.append(
                    f"Parameter '{param.name}': unrecognized unit '{param.unit}'"
                )
                result.checks.append({
                    "check": "unit_check",
                    "status": "warn",
                    "detail": f"{param.name}: unit '{param.unit}' unrecognized",
                })
            else:
                result.checks.append({
                    "check": "unit_check",
                    "status": "pass",
                    "detail": f"{param.name}: unit '{param.unit}' ok",
                })

    def _check_equations(self, spec: SimulationSpecification, result: ValidationResult) -> None:
        for eq in spec.equations:
            has_latex = bool(eq.latex and len(eq.latex.strip()) > 0)
            has_vars = bool(eq.variables)
            if not has_latex:
                result.warnings.append(f"Equation '{eq.id}': missing LaTeX")
            if not has_vars:
                result.warnings.append(f"Equation '{eq.id}': missing variable descriptions")

            result.checks.append({
                "check": "equation_check",
                "status": "pass" if has_latex else "warn",
                "detail": f"Equation '{eq.id}': latex={'yes' if has_latex else 'no'}, vars={'yes' if has_vars else 'no'}",
            })

    def _check_constraints(self, spec: SimulationSpecification, result: ValidationResult) -> None:
        valid_types = {"physical", "chemical", "mathematical", "biological"}
        for constraint in spec.constraints:
            if constraint.type not in valid_types:
                result.warnings.append(
                    f"Constraint type '{constraint.type}' is non-standard"
                )

    def _validate_physics(self, spec: SimulationSpecification, result: ValidationResult) -> None:
        sim_type = spec.simulation_type.value

        for param in spec.parameters:
            if param.symbol.lower() in PHYSICS_CONSTANTS:
                if param.default != PHYSICS_CONSTANTS[param.symbol.lower()]:
                    result.warnings.append(
                        f"Physics constant '{param.symbol}' should be {PHYSICS_CONSTANTS[param.symbol.lower()]}"
                    )

        if sim_type == "projectile_motion":
            has_angle = any(p.symbol.lower() in ("theta", "angle", "\u03b8") for p in spec.parameters)
            has_velocity = any(p.symbol.lower() in ("v", "v0", "u", "velocity", "speed") for p in spec.parameters)
            has_gravity = any(p.symbol.lower() in ("g", "gravity") for p in spec.parameters)

            issues = []
            if not has_angle: issues.append("angle")
            if not has_velocity: issues.append("initial velocity")
            if not has_gravity: issues.append("gravity")

            if issues:
                result.warnings.append(
                    f"Projectile motion should include: {', '.join(issues)} parameters"
                )

            result.checks.append({
                "check": "physics_completeness",
                "status": "warn" if issues else "pass",
                "detail": f"Projectile parameters: angle={'yes' if has_angle else 'no'}, velocity={'yes' if has_velocity else 'no'}, gravity={'yes' if has_gravity else 'no'}",
            })

        elif sim_type == "electricity":
            has_voltage = any(p.symbol.lower() in ("v", "voltage") for p in spec.parameters)
            has_resistance = any(p.symbol.lower() in ("r", "resistance") for p in spec.parameters)

            if not has_voltage or not has_resistance:
                result.warnings.append("Electricity simulation should include voltage and resistance parameters")

        elif sim_type in ("waves",):
            has_amplitude = any("amp" in p.id for p in spec.parameters)
            has_frequency = any("freq" in p.id for p in spec.parameters)
            if not has_amplitude or not has_frequency:
                result.warnings.append("Wave simulation should include amplitude and frequency parameters")

    def _validate_chemistry(self, spec: SimulationSpecification, result: ValidationResult) -> None:
        for param in spec.parameters:
            if param.unit == "K" and (param.min < 0 or param.max < 0):
                result.errors.append(
                    f"Temperature (K) cannot be negative for '{param.name}'"
                )
                result.checks.append({
                    "check": "absolute_temperature",
                    "status": "fail",
                    "detail": f"{param.name}: negative Kelvin",
                })

        if spec.simulation_type.value == "equilibrium":
            has_concentration = any("conc" in p.id for p in spec.parameters)
            has_temperature = any("temp" in p.id for p in spec.parameters)
            if not has_concentration:
                result.warnings.append("Equilibrium sim should include concentration parameters")
            if not has_temperature:
                result.warnings.append("Equilibrium sim should include temperature parameter")

        if spec.simulation_type.value == "reactions":
            has_catalyst = any("catalyst" in p.id or "cat" in p.id for p in spec.parameters)
            if not has_catalyst:
                result.warnings.append("Reaction sim could benefit from catalyst parameter")

    def _validate_biology(self, spec: SimulationSpecification, result: ValidationResult) -> None:
        if spec.simulation_type.value == "population_growth":
            has_birth_rate = any("birth" in p.id for p in spec.parameters)
            has_death_rate = any("death" in p.id for p in spec.parameters)
            if not has_birth_rate or not has_death_rate:
                result.warnings.append("Population model should include birth and death rate parameters")

            has_carrying_capacity = any("carrying" in p.id or "capacity" in p.id or "k" == p.symbol.lower() for p in spec.parameters)
            if not has_carrying_capacity:
                result.warnings.append("Population model should include carrying capacity for logistic growth")

        if spec.simulation_type.value == "diffusion":
            has_concentration = any("conc" in p.id for p in spec.parameters)
            has_temperature = any("temp" in p.id for p in spec.parameters)
            if not has_concentration:
                result.warnings.append("Diffusion sim should include concentration gradient parameter")

    def _validate_mathematics(self, spec: SimulationSpecification, result: ValidationResult) -> None:
        if spec.simulation_type.value == "functions":
            has_coefficients = any(
                "a" == p.symbol or "b" == p.symbol or "c" == p.symbol
                for p in spec.parameters
            )
            if not has_coefficients:
                result.warnings.append("Function plotting should include coefficient parameters")
