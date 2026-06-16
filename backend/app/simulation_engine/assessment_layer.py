from __future__ import annotations

import json
import uuid

from app.simulation_engine.prompt_understanding_layer import query_llm
from app.simulation_engine.schemas import (
    AssessmentPrompt,
    SimulationSpecification,
    Subject,
)


ASSESSMENT_TEMPLATES: dict[str, list[dict]] = {
    "projectile_motion": [
        {
            "type": "prediction",
            "question": "What happens to the range when you increase the launch angle beyond 45 degrees?",
            "hint": "Think about the horizontal and vertical components of velocity.",
            "difficulty": "medium",
            "learning_goal": "Understand optimal launch angle for maximum range",
        },
        {
            "type": "inquiry",
            "question": "How does changing initial velocity affect time of flight? Does it affect horizontal velocity?",
            "hint": "Time of flight depends only on vertical motion.",
            "difficulty": "medium",
            "learning_goal": "Distinguish between horizontal and vertical components",
        },
        {
            "type": "experimentation",
            "question": "Keep the speed constant. Find the two angles that produce the same range. What do you notice?",
            "hint": "Complementary angles produce the same range in ideal projectile motion.",
            "difficulty": "hard",
            "learning_goal": "Discover complementary angle relationship",
        },
        {
            "type": "reflection",
            "question": "If there were air resistance, which trajectory would change more: high angle or low angle?",
            "hint": "Consider which trajectory spends more time in the air.",
            "difficulty": "hard",
            "learning_goal": "Think about real-world vs ideal projectile motion",
        },
    ],
    "electricity": [
        {
            "type": "prediction",
            "question": "What happens to current when you increase resistance while keeping voltage constant?",
            "hint": "Think about Ohm's Law: I = V/R",
            "difficulty": "easy",
            "learning_goal": "Understand inverse relationship in Ohm's Law",
        },
        {
            "type": "inquiry",
            "question": "If you double the voltage, what happens to power dissipation in the resistor?",
            "hint": "Power P = V^2/R or P = I^2*R",
            "difficulty": "medium",
            "learning_goal": "Explore power relationships in circuits",
        },
        {
            "type": "experimentation",
            "question": "Find a combination of voltage and resistance that produces exactly 0.5A of current. How many solutions exist?",
            "hint": "Multiple V and R combinations can produce the same I.",
            "difficulty": "medium",
            "learning_goal": "Understand that multiple states produce same outcome",
        },
    ],
    "diffusion": [
        {
            "type": "prediction",
            "question": "What happens to the diffusion rate when you increase temperature?",
            "hint": "Particles move faster at higher temperatures.",
            "difficulty": "easy",
            "learning_goal": "Understand temperature effect on diffusion",
        },
        {
            "type": "inquiry",
            "question": "How does particle size affect the rate of diffusion?",
            "hint": "Larger particles experience more resistance in the medium.",
            "difficulty": "medium",
            "learning_goal": "Understand size effects on molecular movement",
        },
        {
            "type": "reflection",
            "question": "How is diffusion in a gas different from diffusion in a liquid? Which is faster and why?",
            "hint": "Consider the spacing and movement of particles in each state.",
            "difficulty": "hard",
            "learning_goal": "Compare diffusion across states of matter",
        },
    ],
}

TOPIC_SPECIFIC_PROMPTS = {
    "prediction": "Generate a 'predict' question that asks the student to predict what will happen when a parameter changes.",
    "inquiry": "Generate an 'inquiry' question that asks the student to investigate a relationship between variables.",
    "experimentation": "Generate an 'experimentation' task that asks the student to design an experiment using the simulation.",
    "reflection": "Generate a 'reflection' prompt that asks the student to connect simulation observations to real-world phenomena.",
}


class AssessmentGenerator:
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm

    def generate(
        self, spec: SimulationSpecification
    ) -> list[AssessmentPrompt]:
        if spec.assessment_prompts and len(spec.assessment_prompts) >= 2:
            return spec.assessment_prompts

        if self.use_llm:
            try:
                return self._llm_generate_assessments(spec)
            except Exception:
                pass

        return self._template_assessments(spec)

    def _llm_generate_assessments(
        self, spec: SimulationSpecification
    ) -> list[AssessmentPrompt]:
        prompt_types = ["prediction", "inquiry", "experimentation", "reflection"]
        params_desc = "\n".join(
            f"  - {p.name} ({p.symbol}): {p.description} [{p.min}-{p.max} {p.unit}]"
            for p in spec.parameters
        )
        objectives_desc = "\n".join(
            f"  - {obj}" for obj in spec.learning_objectives
        )

        llm_prompt = f"""You are an educational assessment designer for interactive STEM simulations.

Simulation Topic: {spec.topic}
Subject: {spec.subject.value}
Type: {spec.simulation_type.value}

Learning Objectives:
{objectives_desc}

Available Parameters:
{params_desc}

Generate 4 assessment prompts (one of each type) that encourage active learning:

1. PREDICTION: Ask what will happen when a parameter changes
2. INQUIRY: Ask about investigating relationships between variables
3. EXPERIMENTATION: Ask the student to design a test using the simulation
4. REFLECTION: Ask to connect simulation observations to real-world phenomena

Return ONLY valid JSON array:
[
  {{
    "type": "prediction",
    "question": "question text",
    "hint": "helpful hint",
    "difficulty": "easy|medium|hard",
    "learning_goal": "what this teaches"
  }}
]

Make questions:
- Specific to this simulation's parameters and topic
- Age-appropriate for {spec.grade_level} level
- Focused on conceptual understanding, not formula memorization
- Encourage experimentation before answering
- Connect to real-world applications where possible

Return ONLY the JSON array. No markdown."""

        response = query_llm(llm_prompt, temperature=0.4)
        response = self._clean_json(response)

        try:
            data = json.loads(response)
            if isinstance(data, list):
                assessments = []
                for i, item in enumerate(data):
                    assessments.append(
                        AssessmentPrompt(
                            id=f"ap_{i+1}",
                            type=item.get("type", "inquiry"),
                            question=item.get("question", ""),
                            hint=item.get("hint", ""),
                            difficulty=item.get("difficulty", "medium"),
                            learning_goal=item.get("learning_goal", ""),
                        )
                    )
                return assessments
        except (json.JSONDecodeError, ValueError):
            pass

        return self._template_assessments(spec)

    def _template_assessments(
        self, spec: SimulationSpecification
    ) -> list[AssessmentPrompt]:
        sim_type = spec.simulation_type.value

        if sim_type in ASSESSMENT_TEMPLATES:
            templates = ASSESSMENT_TEMPLATES[sim_type]
        else:
            templates = self._generic_templates(spec)

        assessments = []
        for i, t in enumerate(templates):
            question = t["question"].replace(
                "{topic}", spec.topic
            ).replace(
                "{subject}", spec.subject.value
            )
            assessments.append(
                AssessmentPrompt(
                    id=f"ap_{i+1}",
                    type=t["type"],
                    question=question,
                    hint=t["hint"],
                    difficulty=t["difficulty"],
                    learning_goal=t["learning_goal"].replace(
                        "{topic}", spec.topic
                    ),
                )
            )

        return assessments

    def _generic_templates(
        self, spec: SimulationSpecification
    ) -> list[dict]:
        param = spec.parameters[0] if spec.parameters else None

        return [
            {
                "type": "prediction",
                "question": f"What do you predict will happen to the {spec.topic} when you change the {param.name if param else 'main parameter'}?",
                "hint": f"Try changing the {param.name if param else 'parameter'} and observe the effect.",
                "difficulty": "easy",
                "learning_goal": f"Develop prediction skills for {spec.topic}",
            },
            {
                "type": "inquiry",
                "question": f"How does changing one variable affect other variables in this {spec.topic} simulation?",
                "hint": "Change only one parameter at a time and observe all changes.",
                "difficulty": "medium",
                "learning_goal": f"Understand relationships in {spec.topic}",
            },
            {
                "type": "experimentation",
                "question": f"Design an experiment using this simulation to discover the most important factor affecting {spec.topic}.",
                "hint": "Try extreme values and compare results systematically.",
                "difficulty": "medium",
                "learning_goal": f"Develop experimental design skills",
            },
            {
                "type": "reflection",
                "question": f"Where have you observed {spec.topic} in real life? Does this simulation match your real-world observations?",
                "hint": "Think about everyday examples of this concept.",
                "difficulty": "easy",
                "learning_goal": f"Connect {spec.topic} to real-world phenomena",
            },
        ]

    def _clean_json(self, response: str) -> str:
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
