from __future__ import annotations

from app.simulation_engine.schemas import ValidationResult


class UIQualityChecker:
    REQUIRED_ELEMENTS = [
        "canvas",
        "title",
        "controls",
        "sliders",
        "reset",
        "play_pause",
        "live_values",
    ]

    ACCESSIBILITY_CHECKS = [
        "aria_labels",
        "keyboard_nav",
        "color_contrast",
        "focus_indicators",
    ]

    RESPONSIVE_CHECKS = [
        "viewport_meta",
        "relative_units",
        "media_queries",
        "touch_targets",
    ]

    def check(self, html: str) -> ValidationResult:
        result = ValidationResult(passed=True, score=1.0)
        html_lower = html.lower()

        self._check_required_elements(html_lower, result)
        self._check_responsive(html_lower, result)
        self._check_accessibility(html_lower, result)
        self._check_animations(html_lower, result)
        self._check_educational_layout(html_lower, result)

        total_checks = len(result.checks)
        total_errors = len(result.errors)
        total_warnings = len(result.warnings)

        if total_checks > 0:
            result.score = max(
                0.0, 1.0 - (total_errors * 0.3 + total_warnings * 0.1)
            )
        result.passed = total_errors == 0 and result.score >= 0.7

        return result

    def _check_required_elements(self, html: str, result: ValidationResult) -> None:
        element_map = {
            "canvas": "canvas",
            "simulation title": "title",
            "parameter sliders": 'type="range"',
            "controls section": "controls",
            "reset button": "reset",
            "animation loop": "requestanimationframe",
            "live value display": "live",
        }

        for name, pattern in element_map.items():
            found = pattern in html
            result.checks.append({
                "check": f"required_element_{name.replace(' ', '_')}",
                "status": "pass" if found else "fail",
                "detail": f"{name}: {'found' if found else 'missing'}",
            })
            if not found:
                result.errors.append(f"Missing required element: {name}")

    def _check_responsive(self, html: str, result: ValidationResult) -> None:
        checks = {
            "viewport meta tag": "viewport",
            "responsive canvas": "max-width: 100%",
        }

        for name, pattern in checks.items():
            found = pattern in html
            result.checks.append({
                "check": f"responsive_{name.replace(' ', '_')}",
                "status": "pass" if found else "warn",
                "detail": f"{name}: {'found' if found else 'missing'}",
            })
            if not found:
                result.warnings.append(f"Responsive issue: {name}")

    def _check_accessibility(self, html: str, result: ValidationResult) -> None:
        checks = {
            "aria labels": "aria-",
            "keyboard support": "keydown",
            "semantic HTML": "<main",
        }

        for name, pattern in checks.items():
            found = pattern in html
            result.checks.append({
                "check": f"accessibility_{name.replace(' ', '_')}",
                "status": "pass" if found else "warn",
                "detail": f"{name}: {'found' if found else 'missing'}",
            })
            if not found:
                result.warnings.append(f"Accessibility: {name}")

    def _check_animations(self, html: str, result: ValidationResult) -> None:
        html_lower = html.lower()
        has_rAF = "requestanimationframe" in html_lower
        has_delta_time = "deltatime" in html_lower or "delta_time" in html_lower or " dt " in html_lower

        result.checks.append({
            "check": "animation_performance",
            "status": "pass" if has_rAF else "fail",
            "detail": f"requestAnimationFrame: {'found' if has_rAF else 'missing'}",
        })
        if not has_rAF:
            result.errors.append("Animation must use requestAnimationFrame")

        result.checks.append({
            "check": "delta_time",
            "status": "pass" if has_delta_time else "warn",
            "detail": f"Delta time: {'found' if has_delta_time else 'missing - animations may be frame-rate dependent'}",
        })
        if not has_delta_time:
            result.warnings.append("Missing delta-time: animations may be frame-rate dependent")

    def _check_educational_layout(self, html: str, result: ValidationResult) -> None:
        checks = {
            "learning objective": "learning-objective",
            "simulation area": "simulation-area",
            "graph display": "graph",
            "parameter controls": "controls",
            "assessment": "assessment",
        }

        for name, pattern in checks.items():
            found = pattern in html
            result.checks.append({
                "check": f"educational_layout_{name.replace(' ', '_')}",
                "status": "pass" if found else "warn",
                "detail": f"{name}: {'found' if found else 'missing'}",
            })
            if not found:
                result.warnings.append(f"Educational layout: {name}")
