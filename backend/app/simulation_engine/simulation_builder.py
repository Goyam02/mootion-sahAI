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
        from app.simulation_engine.templates.base_template import build_simulation_html, build_custom_llm_simulation
        
        # Always dynamically generate the core JS classes using the LLM for high creativity
        js_code = build_custom_llm_simulation(spec)
        html = build_simulation_html(spec, custom_script=js_code)
        
        # Self-healing loop: retry up to 3 times if there are validation issues
        retries = 3
        for attempt in range(retries):
            issues = self.validate_html(html)
            if not issues:
                break
                
            print(f"[SimulationBuilder] Validation failed on attempt {attempt + 1}: {issues}. Retrying self-healing...")
            js_code = self.heal_js_code(spec, js_code, issues)
            html = build_simulation_html(spec, custom_script=js_code)
            
        return html

    def heal_js_code(self, spec: SimulationSpecification, bad_js: str, issues: list[str]) -> str:
        from app.simulation_engine.prompt_understanding_layer import query_llm

        issues_text = "\n".join(f"- {issue}" for issue in issues)
        
        prompt = f"""You are an expert frontend developer and creative tech designer.
A previously generated JavaScript code block for a simulation has failed validation/compilation.
Your job is to fix the errors and provide the corrected version of the JavaScript code.

TOPIC: {spec.topic}
SUBJECT: {spec.subject.value.upper() if spec.subject else "SIMULATION"}
LEARNING OBJECTIVES: {"; ".join(spec.learning_objectives) if spec.learning_objectives else spec.topic}

━━ ISSUES TO FIX ━━
{issues_text}

━━ PREVIOUS GENERATED CODE ━━
{bad_js}

━━ REQUIREMENTS & CRITICAL INSTRUCTIONS ━━
1. Output ONLY the raw JavaScript code defining:
   - `class SimulationEngine`
   - `class Renderer`
2. Do NOT include any code markdown blocks (no ```javascript or ```), HTML, or explanation. Start directly with the classes.
3. Make sure all issues listed above are fully fixed. For example:
   - If there is a SyntaxError (e.g., "Identifier 'xxx' has already been declared"), resolve the duplicate variable declaration or scope issue.
   - If a class is missing (e.g., StateManager, ControlsManager, etc.), remember that StateManager, ControlsManager, and EventBus are already provided globally by the template wrapper. Do NOT re-declare them in your JS code, but ensure that your SimulationEngine and Renderer conform to what the template expects.
   - Ensure the required classes `SimulationEngine` and `Renderer` are fully implemented, and that `SimulationEngine` has `canvasInteractions(canvas, state, bus)` implemented.
   - Keep the visual designs premium with white backgrounds, royal blue `#1800ad` accents, and a clean HUD overlay.
"""
        try:
            js_code = query_llm(prompt, temperature=0.1)
            js_code = js_code.strip()
            
            # strip markdown fences if model ignores instructions
            if js_code.startswith("```"):
                js_code = js_code[js_code.find("\n") + 1:]
            if js_code.endswith("```"):
                js_code = js_code[:-3].rstrip()
            js_code = js_code.strip()

            # Sanity-check
            if "class SimulationEngine" not in js_code or "class Renderer" not in js_code:
                return bad_js

            # Strip any ControlsManager/AssessmentEngine the model may have hallucinated
            for cls in ("class ControlsManager", "class AssessmentEngine"):
                idx = js_code.find(cls)
                if idx != -1:
                    js_code = js_code[:idx].rstrip()

            return js_code
        except Exception as e:
            print(f"Error in self-healing LLM query: {e}")
            return bad_js

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

        # Hardened syntax validation via Node.js syntax compiler (node -c -)
        start_tag = "<script>"
        end_tag = "</script>"
        start_idx = html.find(start_tag)
        end_idx = html.find(end_tag)
        if start_idx != -1 and end_idx != -1:
            js_code = html[start_idx + len(start_tag):end_idx]
            import subprocess
            try:
                proc = subprocess.run(
                    ["node", "-c", "-"],
                    input=js_code,
                    capture_output=True,
                    text=True,
                    timeout=2.0
                )
                if proc.returncode != 0:
                    error_msg = proc.stderr.strip().split("\n")[0]
                    # Clean up node internal stack trace lines
                    clean_msg = error_msg.replace("[stdin]:", "Line ")
                    issues.append(f"JavaScript syntax error: {clean_msg}")
            except Exception as e:
                # If node is unavailable in testing/prod container, log and bypass syntax check
                print(f"Bypassing JS syntax validation: {e}")

        return issues
