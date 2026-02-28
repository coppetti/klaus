"""
Memory Relevance Gate
=====================
Intelligent filter that scores each conversation turn before persisting to memory.
Reuses ContextAnalyzer scoring logic from context_compactor.py.

Decision logic:
  score >= 0.6  →  SAVE, importance="high", extract structured facts
  score >= 0.3  →  SAVE, importance="medium", raw summary
  score <  0.3  →  SKIP (greetings, acks, noise)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from core.context_compactor import ContextAnalyzer


# ---------------------------------------------------------------------------
# Thresholds (can be overridden via init.yaml: memory.relevance_threshold)
# ---------------------------------------------------------------------------
HIGH_THRESHOLD = 0.6
LOW_THRESHOLD  = 0.3

# Short noise messages to skip regardless of score
NOISE_PATTERNS = [
    r"^(ok|oi|olá|ola|hi|hey|hello|thanks|obrigado|obrigada|tks|thx|👍|✅|sure|yep|yes|no|sim|não|nao|certo|beleza|entendido|got it|cool|nice|perfect|perfeito|ótimo|otimo|exato|claro|claro!|👋)\.?$",
]


@dataclass
class RelevanceDecision:
    """Result of evaluating a conversation turn."""
    should_store: bool
    importance: str          # "high" | "medium" | "low"
    score: float             # Raw score from ContextAnalyzer
    extracted_facts: List[str] = field(default_factory=list)
    skip_reason: Optional[str] = None


class MemoryRelevanceGate:
    """
    Gates memory persistence based on relevance scoring.

    Usage:
        gate = MemoryRelevanceGate()
        decision = gate.evaluate(user_msg, assistant_msg)
        if decision.should_store:
            memory.store(
                content=decision.extracted_facts[0] if decision.extracted_facts else summary,
                importance=decision.importance
            )
    """

    def __init__(
        self,
        high_threshold: float = HIGH_THRESHOLD,
        low_threshold: float  = LOW_THRESHOLD,
    ):
        self.high_threshold = high_threshold
        self.low_threshold  = low_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, user_msg: str, assistant_msg: str) -> RelevanceDecision:
        """Score the interaction and return a persistence decision."""

        # 1. Quick noise check on the user side
        if self._is_noise(user_msg):
            return RelevanceDecision(
                should_store=False,
                importance="low",
                score=0.0,
                skip_reason=f"noise pattern: '{user_msg[:30]}'"
            )

        # 2. Score combined message using existing ContextAnalyzer
        combined = {"text": f"{user_msg}\n{assistant_msg}", "sender": "user", "id": 0}
        importance_obj = ContextAnalyzer.analyze_importance(combined, [combined])
        score = importance_obj.importance_score

        # 3. Apply keyword boost for strong signal words missed by ContextAnalyzer
        #    (covers Portuguese phrases and domain-specific patterns)
        score = min(1.0, score + self._keyword_boost(user_msg))

        # 4. Decision branching
        if score >= self.high_threshold:
            facts = self._extract_facts(user_msg, assistant_msg)
            return RelevanceDecision(
                should_store=True,
                importance="high",
                score=score,
                extracted_facts=facts,
            )
        elif score >= self.low_threshold:
            return RelevanceDecision(
                should_store=True,
                importance="medium",
                score=score,
                extracted_facts=[],
            )
        else:
            return RelevanceDecision(
                should_store=False,
                importance="low",
                score=score,
                skip_reason=f"score {score:.2f} below threshold {self.low_threshold}"
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_noise(self, text: str) -> bool:
        """Return True if text matches known noise patterns."""
        cleaned = text.strip().lower()
        for pattern in NOISE_PATTERNS:
            if re.fullmatch(pattern, cleaned, re.IGNORECASE):
                return True
        return False

    def _keyword_boost(self, text: str) -> float:
        """
        Return additive score boost based on high-signal keyword categories.
        Compensates for gaps in ContextAnalyzer's Portuguese keyword coverage.
        """
        text_lower = text.lower()
        boost = 0.0

        # Decisions (+0.35) — strongest signal
        DECISION_WORDS = [
            'vamos usar', 'vou usar', 'decidimos', 'decidi',
            'adotar', 'vamos adotar', 'escolhi', 'let\'s use',
            'we\'ll use', 'decided', 'we decided',
        ]
        for w in DECISION_WORDS:
            if w in text_lower:
                boost += 0.35
                break

        # Preferences (+0.30)
        PREF_WORDS = [
            'prefiro', 'prefiro sempre', 'gosto de', 'não gosto',
            'prefer', 'always use', 'nunca uso', 'avoid',
            'quero sempre', 'I want', 'I always',
        ]
        for w in PREF_WORDS:
            if w in text_lower:
                boost += 0.30
                break

        # Problems/Bugs (+0.25)
        PROBLEM_WORDS = [
            'bug', 'erro', 'error', 'problema', 'broken',
            'não funciona', 'not working', 'fails', 'falha',
        ]
        for w in PROBLEM_WORDS:
            if w in text_lower:
                boost += 0.25
                break

        # Success markers (+0.20)
        SUCCESS_WORDS = [
            'funcionou', 'solved', 'resolvido', 'success',
            'worked', 'implementei', 'implemented',
        ]
        for w in SUCCESS_WORDS:
            if w in text_lower:
                boost += 0.20
                break

        return min(boost, 0.5)  # Cap total boost at 0.5

    def _extract_facts(self, user_msg: str, assistant_msg: str) -> List[str]:
        """
        Extract concise, structured facts from a high-importance interaction.
        Returns a list of short factual statements suitable for memory storage.
        """
        facts: List[str] = []

        # Fact type 1: Decisions ("vamos usar X", "decided to use X")
        decision_patterns = [
            r"(vamos usar|let'?s use|we'?ll use|adotamos|chose|decidimos|decided)\s+(.{3,60})",
            r"(a solução é|the solution is|the approach is|approach:\s*)(.{3,80})",
        ]
        for pattern in decision_patterns:
            match = re.search(pattern, user_msg + " " + assistant_msg, re.IGNORECASE)
            if match:
                facts.append(f"Decision: {match.group(0)[:120]}")

        # Fact type 2: Code artefacts (function/class names mentioned)
        code_refs = re.findall(r"`([^`]{3,40})`", assistant_msg)
        if code_refs:
            facts.append(f"Code: {', '.join(code_refs[:5])}")

        # Fact type 3: Preferences stated by user
        pref_patterns = [
            r"(prefiro|prefer|gosto de|like|sempre uso|always use|I want)\s+(.{3,60})",
            r"(não gosto de|don'?t like|nunca uso|never use|avoid)\s+(.{3,60})",
        ]
        for pattern in pref_patterns:
            match = re.search(pattern, user_msg, re.IGNORECASE)
            if match:
                facts.append(f"Preference: {match.group(0)[:100]}")

        # Fallback: if no structured facts found, use truncated Q/A
        if not facts:
            facts.append(f"Q: {user_msg[:100]} | A: {assistant_msg[:200]}")

        return facts
def should_store_memory(content: str) -> bool:
    """Convenience wrapper for checking memory relevance."""
    # Simple heuristic for single-message evaluation
    if not content or len(content.strip()) < 10:
        return False
    
    text = content.lower().strip()
    
    # Noise patterns
    noise = [
        r"^(ok|oi|olá|ola|hi|hey|hello|thanks|obrigado|obrigada|tks|thx|sure|yep|yes|no|sim|não|nao|certo|beleza|entendido|got it|cool|nice|perfect|perfeito|ótimo|otimo|exato|claro|👋)\b",
    ]
    import re
    for pattern in noise:
        if re.match(pattern, text):
            return False
    
    # Identity questions
    identity = [
        r"quem.*(é|eh|e).*(voce|vc|tu|você)",
        r"who.*(are|r).*(you|u)",
    ]
    for pattern in identity:
        if re.search(pattern, text):
            return False
    
    return True
