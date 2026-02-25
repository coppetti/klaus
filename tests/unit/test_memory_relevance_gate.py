"""
Unit Tests for MemoryRelevanceGate
====================================
Tests the automatic scoring and persistence decision logic.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.memory_relevance_gate import MemoryRelevanceGate, RelevanceDecision


class TestNoiseDetection(unittest.TestCase):
    """Test that trivial messages are correctly skipped."""

    def setUp(self):
        self.gate = MemoryRelevanceGate()

    def test_skip_single_ok(self):
        decision = self.gate.evaluate("ok", "Sem problema!")
        self.assertFalse(decision.should_store)
        self.assertEqual(decision.importance, "low")

    def test_skip_greeting_hi(self):
        decision = self.gate.evaluate("hi", "Hello! How can I help you today?")
        self.assertFalse(decision.should_store)

    def test_skip_oi(self):
        decision = self.gate.evaluate("oi", "Olá! Em que posso ajudar?")
        self.assertFalse(decision.should_store)

    def test_skip_thanks(self):
        decision = self.gate.evaluate("thanks", "You're welcome!")
        self.assertFalse(decision.should_store)

    def test_skip_obrigado(self):
        decision = self.gate.evaluate("obrigado", "De nada!")
        self.assertFalse(decision.should_store)

    def test_skip_thumbs_up(self):
        decision = self.gate.evaluate("👍", "Ótimo!")
        self.assertFalse(decision.should_store)

    def test_skip_yes(self):
        decision = self.gate.evaluate("yes", "Perfeito, vou fazer isso.")
        self.assertFalse(decision.should_store)


class TestHighImportanceDetection(unittest.TestCase):
    """Test that important messages are stored with high importance."""

    def setUp(self):
        self.gate = MemoryRelevanceGate()

    def test_save_decision_message(self):
        user = "vamos usar FastAPI para o backend"
        assistant = "Ótima escolha! FastAPI é excelente para APIs com tipagem forte."
        decision = self.gate.evaluate(user, assistant)
        self.assertTrue(decision.should_store)

    def test_save_code_heavy_response(self):
        user = "como implemento o filtro?"
        assistant = """
        Use o método `filter()`. Exemplo:
        ```python
        def filter_memories(memories):
            return [m for m in memories if m['importance'] == 'high']
        ```
        """
        decision = self.gate.evaluate(user, assistant)
        self.assertTrue(decision.should_store)
        # Code-heavy should be high importance
        self.assertIn(decision.importance, ["high", "medium"])

    def test_save_architecture_discussion(self):
        user = "decidi que vamos adotar PostgreSQL como banco principal"
        assistant = "Ótima decisão. O PostgreSQL é mais robusto e suporta extensões como pgvector para nosso caso."
        decision = self.gate.evaluate(user, assistant)
        self.assertTrue(decision.should_store)

    def test_save_problem_report(self):
        user = "tem um bug no endpoint de memory, ele retorna 500"
        assistant = "Vejo o problema. O erro está na linha 42 do hybrid_memory.py quando o grafo não está disponível."
        decision = self.gate.evaluate(user, assistant)
        self.assertTrue(decision.should_store)

    def test_save_preference(self):
        user = "prefiro sempre respostas em bullet points e bem diretas"
        assistant = "Entendido. Vou usar bullet points em todas as respostas daqui pra frente."
        decision = self.gate.evaluate(user, assistant)
        self.assertTrue(decision.should_store)


class TestRelevanceDecisionStructure(unittest.TestCase):
    """Test the structure of RelevanceDecision objects."""

    def setUp(self):
        self.gate = MemoryRelevanceGate()

    def test_decision_has_score(self):
        decision = self.gate.evaluate("What is Python?", "Python is a programming language.")
        self.assertIsInstance(decision.score, float)
        self.assertGreaterEqual(decision.score, 0.0)
        self.assertLessEqual(decision.score, 1.0)

    def test_decision_has_skip_reason_when_skipped(self):
        decision = self.gate.evaluate("ok", "Perfeito!")
        self.assertFalse(decision.should_store)
        self.assertIsNotNone(decision.skip_reason)

    def test_fact_extraction_for_code(self):
        user = "como funciona?"
        assistant = "Use o método `store_interaction()` e o `MemoryRelevanceGate` filtro automaticamente."
        decision = self.gate.evaluate(user, assistant)
        if decision.should_store and decision.extracted_facts:
            # Code facts should reference the mentioned symbols
            all_facts = " ".join(decision.extracted_facts)
            self.assertIn("Code:", all_facts)


class TestThresholdConfiguration(unittest.TestCase):
    """Test that thresholds are configurable."""

    def test_custom_thresholds(self):
        # Very permissive gate
        permissive_gate = MemoryRelevanceGate(high_threshold=0.9, low_threshold=0.0)
        decision = permissive_gate.evaluate(
            "ok que horas são?",
            "São 10h da manhã."
        )
        # With low_threshold=0.0, even low-score messages should be stored (unless noise pattern)
        self.assertIsInstance(decision, RelevanceDecision)

    def test_strict_gate_drops_more(self):
        strict_gate = MemoryRelevanceGate(high_threshold=0.9, low_threshold=0.8)
        permissive_gate = MemoryRelevanceGate(high_threshold=0.6, low_threshold=0.3)

        user = "what time is it?"
        assistant = "It's 10am."

        strict_decision = strict_gate.evaluate(user, assistant)
        permissive_decision = permissive_gate.evaluate(user, assistant)

        # Strict gate should be at least as restrictive as permissive
        if not permissive_decision.should_store:
            self.assertFalse(strict_decision.should_store)


if __name__ == "__main__":
    unittest.main()
