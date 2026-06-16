from __future__ import annotations

import json
import re
import time
from difflib import SequenceMatcher

from app.core.config import settings
from app.simulation_engine.schemas import (
    SimulationIntent,
    Subject,
    SimulationType,
    SimulationPhase,
)

SUBJECT_KEYWORDS: dict[Subject, list[str]] = {
    Subject.PHYSICS: [
        "force", "motion", "energy", "velocity", "acceleration", "gravity",
        "projectile", "kinematics", "newton", "momentum", "work", "power",
        "electric", "magnetic", "wave", "sound", "light", "optics", "circuit",
        "voltage", "current", "resistance", "capacitor", "inductor", "field",
        "thermodynamic", "heat", "temperature", "quantum", "relativity",
        "nuclear", "atomic", "particle", "mechanics", "fluid", "pressure",
        "oscillation", "frequency", "amplitude", "wavelength", "spectrum",
    ],
    Subject.CHEMISTRY: [
        "atom", "molecule", "element", "compound", "bond", "reaction",
        "acid", "base", "salt", "oxidation", "reduction", "redox",
        "electron", "proton", "neutron", "orbital", "shell", "valence", "atomic",
        "periodic", "table", "group", "period", "ion", "isotope",
        "polarity", "electronegativity", "hybridization", "equilibrium",
        "concentration", "molarity", "stoichiometry", "enthalpy",
        "entropy", "gibbs", "catalyst", "rate", "kinetics", "solution",
        "solubility", "precipitation", "titration", "buffer", "ph",
    ],
    Subject.BIOLOGY: [
        "cell", "membrane", "transport", "diffusion", "osmosis",
        "organelle", "nucleus", "mitochondria", "chloroplast", "dna",
        "rna", "gene", "genetic", "chromosome", "allele", "trait",
        "protein", "enzyme", "metabolism", "photosynthesis",
        "respiration", "mitosis", "meiosis", "evolution", "natural selection",
        "population", "ecosystem", "habitat", "food chain", "symbiosis",
        "neuron", "synapse", "muscle", "tissue", "organ", "system",
        "immune", "antibody", "vaccine", "virus", "bacteria", "fungus",
        "homeostasis", "feedback", "hormone", "reproduction",
    ],
    Subject.MATHEMATICS: [
        "function", "graph", "equation", "derivative", "integral",
        "limit", "sequence", "series", "matrix", "vector", "geometry",
        "triangle", "circle", "angle", "probability", "statistic",
        "mean", "median", "mode", "deviation", "correlation",
        "regression", "distribution", "permutation", "combination",
        "polynomial", "quadratic", "linear", "exponential", "logarithm",
        "trigonometry", "sin", "cos", "tan", "calculus", "differential",
        "coordinate", "slope", "intercept", "theorem", "proof",
    ],
}

SIMULATION_TYPE_MAP: list[tuple[Subject, str, SimulationType]] = [
    (Subject.PHYSICS, "projectile", SimulationType.PROJECTILE_MOTION),
    (Subject.PHYSICS, "kinematics", SimulationType.KINEMATICS),
    (Subject.PHYSICS, "force", SimulationType.FORCES),
    (Subject.PHYSICS, "forces", SimulationType.FORCES),
    (Subject.PHYSICS, "energy", SimulationType.ENERGY),
    (Subject.PHYSICS, "electric", SimulationType.ELECTRICITY),
    (Subject.PHYSICS, "circuit", SimulationType.ELECTRICITY),
    (Subject.PHYSICS, "wave", SimulationType.WAVES),
    (Subject.PHYSICS, "sound", SimulationType.WAVES),
    (Subject.PHYSICS, "buoyancy", SimulationType.BUOYANCY),
    (Subject.PHYSICS, "fluid", SimulationType.BUOYANCY),
    (Subject.PHYSICS, "density", SimulationType.BUOYANCY),
    (Subject.PHYSICS, "float", SimulationType.BUOYANCY),
    (Subject.PHYSICS, "sink", SimulationType.BUOYANCY),
    (Subject.CHEMISTRY, "atom", SimulationType.ATOMIC_STRUCTURE),
    (Subject.CHEMISTRY, "atomic", SimulationType.ATOMIC_STRUCTURE),
    (Subject.CHEMISTRY, "polarity", SimulationType.MOLECULAR_POLARITY),
    (Subject.CHEMISTRY, "bond", SimulationType.BONDING),
    (Subject.CHEMISTRY, "reaction", SimulationType.REACTIONS),
    (Subject.CHEMISTRY, "equilibrium", SimulationType.EQUILIBRIUM),
    (Subject.BIOLOGY, "membrane", SimulationType.MEMBRANE_TRANSPORT),
    (Subject.BIOLOGY, "diffusion", SimulationType.DIFFUSION),
    (Subject.BIOLOGY, "genetic", SimulationType.GENETICS),
    (Subject.BIOLOGY, "population", SimulationType.POPULATION_GROWTH),
    (Subject.BIOLOGY, "cell", SimulationType.CELL_BIOLOGY),
    (Subject.MATHEMATICS, "function", SimulationType.FUNCTIONS),
    (Subject.MATHEMATICS, "functions", SimulationType.FUNCTIONS),
    (Subject.MATHEMATICS, "geometry", SimulationType.GEOMETRY),
    (Subject.MATHEMATICS, "probability", SimulationType.PROBABILITY),
    (Subject.MATHEMATICS, "statistic", SimulationType.STATISTICS),
]


def query_llm(prompt: str, temperature: float = 0.2) -> str:
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        raise RuntimeError("Azure OpenAI is not configured")

    from openai import OpenAI

    client = OpenAI(
        base_url=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )

    response = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content or ""


class PromptUnderstandingLayer:
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm

    def understand(self, prompt: str) -> SimulationIntent:
        prompt_lower = prompt.lower()

        subject = self._classify_subject(prompt_lower)
        simulation_type = self._determine_simulation_type(prompt_lower, subject)
        concepts = self._extract_concepts(prompt_lower, subject)
        topic = self._extract_topic(prompt, prompt_lower, subject, concepts)

        if self.use_llm:
            try:
                llm_intent = self._llm_enhanced_understanding(prompt)
                if llm_intent and llm_intent.confidence > 0.5:
                    return llm_intent
            except Exception:
                pass

        return SimulationIntent(
            subject=subject,
            topic=topic,
            concepts=concepts,
            simulation_type=simulation_type,
            grade_level=self._estimate_grade_level(prompt_lower),
            confidence=0.7,
            raw_prompt=prompt,
        )

    @staticmethod
    def _word_in_text(word: str, text: str) -> bool:
        return bool(re.search(r'\b' + re.escape(word) + r'\b', text))

    def _classify_subject(self, prompt_lower: str) -> Subject:
        scores: dict[Subject, float] = {}
        for subject, keywords in SUBJECT_KEYWORDS.items():
            score = sum(2 for kw in keywords if self._word_in_text(kw, prompt_lower))
            score += sum(
                1.5
                for kw in keywords
                if SequenceMatcher(None, kw, prompt_lower).ratio() > 0.8
            )
            scores[subject] = score
        if not scores or max(scores.values()) == 0:
            return Subject.PHYSICS
        max_score = max(scores.values())
        top = [s for s, sc in scores.items() if sc == max_score]
        if len(top) == 1:
            return top[0]
        for subject in top:
            if self._determine_simulation_type(prompt_lower, subject) != SimulationType.CUSTOM:
                return subject
        return top[0]

    def _determine_simulation_type(
        self, prompt_lower: str, subject: Subject
    ) -> SimulationType:
        for sim_subject, keyword, sim_type in SIMULATION_TYPE_MAP:
            if sim_subject == subject and self._word_in_text(keyword, prompt_lower):
                return sim_type
        return SimulationType.CUSTOM

    def _extract_concepts(self, prompt_lower: str, subject: Subject) -> list[str]:
        concepts = []
        for kw in SUBJECT_KEYWORDS.get(subject, []):
            if self._word_in_text(kw, prompt_lower):
                concepts.append(kw)
        return concepts[:5]

    def _extract_topic(
        self,
        prompt: str,
        prompt_lower: str,
        subject: Subject,
        concepts: list[str],
    ) -> str:
        STOP_PHRASES = [
            "explain", "teach", "show", "demonstrate", "help", "what is",
            "how does", "simulate", "generate", "create", "make",
        ]

        clean = prompt.strip()
        for phrase in STOP_PHRASES:
            if clean.lower().startswith(phrase):
                clean = clean[len(phrase) :].strip()
                break

        clean = clean.strip(" ?.!,:;")
        if not clean:
            return concepts[0].title() if concepts else prompt

        return clean[:80]

    def _estimate_grade_level(self, prompt_lower: str) -> str:
        advanced = [
            "quantum", "relativity", "lagrangian", "hamiltonian",
            "schrodinger", "maxwell", "thermodynamics",
            "organic synthesis", "molecular orbital",
        ]
        basic = [
            "basic", "simple", "beginner", "introduction",
            "what is", "kid", "child", "elementary",
        ]

        for word in advanced:
            if word in prompt_lower:
                return "advanced"
        for word in basic:
            if word in prompt_lower:
                return "middle_school"
        return "high_school"

    def _llm_enhanced_understanding(self, prompt: str) -> SimulationIntent | None:
        llm_prompt = f"""Analyze this student request for an educational simulation and extract structured intent.

Student Prompt: "{prompt}"

Return ONLY valid JSON with these fields:
{{
  "subject": "physics|chemistry|biology|mathematics",
  "topic": "specific topic name (max 5 words)",
  "concepts": ["concept1", "concept2", ...],
  "simulation_type": "specific type matching the topic",
  "grade_level": "middle_school|high_school|advanced",
  "confidence": 0.0-1.0
}}

Rules:
- subject must be one of: physics, chemistry, biology, mathematics
- simulation_type should be descriptive (e.g., "projectile_motion", "diffusion", "molecular_polarity")
- concepts should list 1-5 key STEM concepts
- grade_level defaults to high_school unless prompt indicates otherwise
- confidence reflects how certain you are of the classification
- Return ONLY the JSON object, no markdown, no explanation."""

        response = query_llm(llm_prompt, temperature=0.1)
        response = response.strip()

        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        try:
            data = json.loads(response)
            return SimulationIntent(
                subject=Subject(data.get("subject", "physics")),
                topic=data.get("topic", ""),
                concepts=data.get("concepts", []),
                simulation_type=SimulationType(
                    data.get("simulation_type", "custom")
                ),
                grade_level=data.get("grade_level", "high_school"),
                confidence=float(data.get("confidence", 0.7)),
                raw_prompt=prompt,
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            return None
