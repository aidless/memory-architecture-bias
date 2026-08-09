"""Smoke tests for the PAPER5 reproduce_peer harness.

Run:
    python -m pytest tests/test_reproduce_peer.py -v
    # or, if pytest not installed:
    python tests/test_reproduce_peer.py

These tests are the contract that the harness matches protocol.md.
They exercise:
  - seed_for is deterministic
  - condition registry covers the 15 canonical conditions + 1 probe
  - gamma_temporal on synthetic JSONL returns a finite number
  - load_corpus caches to disk
  - gamma_decomposition handles all three architectures
"""
from __future__ import annotations
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reproduce_peer import seed_for, CONDITIONS, CONDITION_GROUPS  # noqa: E402
from reproduce_peer.condition_registry import get as get_condition  # noqa: E402
from reproduce_peer.load_corpus import (  # noqa: E402
    load_passages, CORPUS_PATH, N_PASSAGES, BASE_SEED as CORPUS_BASE_SEED,
)
from scoring import (  # noqa: E402
    gamma_temporal, gamma_content, gamma_retrieval, gamma_decomposition,
    ece, delta_ece, bootstrap_ci,
)


class SeedLockTests(unittest.TestCase):
    def test_deterministic(self):
        a = seed_for("D-A-08", 3, "agent_A", "bias_mask")
        b = seed_for("D-A-08", 3, "agent_A", "bias_mask")
        self.assertEqual(a, b)

    def test_distinct_purposes(self):
        s_bias = seed_for("D-A-08", 3, "agent_A", "bias_mask")
        s_svd = seed_for("D-A-08", 3, "agent_A", "svd")
        self.assertNotEqual(s_bias, s_svd)

    def test_in_range(self):
        s = seed_for("Q-S-AU", 7, "agent_B", "bootstrap")
        self.assertGreaterEqual(s, 0)
        self.assertLess(s, 2**32)


class ConditionRegistryTests(unittest.TestCase):
    def test_canonical_count(self):
        canonical = [c for c in CONDITIONS if c.is_canonical]
        self.assertEqual(len(canonical), 15)

    def test_sensitivity_probe_present(self):
        probe = [c for c in CONDITIONS if not c.is_canonical]
        self.assertEqual(len(probe), 1)
        self.assertEqual(probe[0].condition_id, "D-R-DENSE-05")

    def test_unique_ids(self):
        ids = [c.condition_id for c in CONDITIONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_deepseek_face1(self):
        ids = CONDITION_GROUPS["deepseek_length"]
        self.assertEqual(len(ids), 9)
        for cid in ids:
            c = get_condition(cid)
            self.assertEqual(c.model, "deepseek")
            self.assertEqual(c.bias_type, "length")
            self.assertEqual(c.n_rounds, 30)
            self.assertEqual(c.n_seeds, 10)

    def test_qwen_face2(self):
        length = CONDITION_GROUPS["qwen_length"]
        authority = CONDITION_GROUPS["qwen_authority"]
        self.assertEqual(len(length), 3)
        self.assertEqual(len(authority), 3)

    def test_sensitivity_theta(self):
        probe = get_condition("D-R-DENSE-05")
        self.assertAlmostEqual(probe.theta, 0.3)
        self.assertAlmostEqual(probe.p, 0.5)


class GammaMonitorTests(unittest.TestCase):
    def test_gamma_temporal_finite(self):
        # Verify gamma_temporal returns a finite, non-negative number on
        # synthetic input. Both constant-length and varying-length inputs
        # are valid; only finiteness + non-negativity is contracted here.
        # (Real length-shift behaviour is covered indirectly by the
        # existing main.tex table regenerations.)
        for clean, biased in [
            # identical constant-length arms -> gamma == 0
            ([{"output_text": "a " * 10} for _ in range(30)],
             [{"output_text": "a " * 10} for _ in range(30)]),
            # varying-length arms -> gamma >= 0 and finite
            ([{"output_text": "a " * (5 + i)} for i in range(30)],
             [{"output_text": "b " * (10 + i)} for i in range(30)]),
        ]:
            g = gamma_temporal(clean, biased)
            self.assertTrue(math.isfinite(g), f"non-finite gamma={g}")
            self.assertGreaterEqual(g, 0.0, f"negative gamma={g}")

    def test_gamma_temporal_zero_for_identical(self):
        rows = [{"output_text": "same length token count here"} for _ in range(30)]
        g = gamma_temporal(rows, rows)
        self.assertAlmostEqual(g, 0.0, places=6)

    def test_gamma_decomposition_append_only(self):
        # For Append-Only / RAG, gamma_content == gamma_temporal, retrieval == 0
        g, r = gamma_decomposition(0.42, "Append-Only")
        self.assertAlmostEqual(g, 0.42)
        self.assertAlmostEqual(r, 0.0)

    def test_gamma_decomposition_summarization_raises(self):
        with self.assertRaises(ValueError):
            gamma_decomposition(0.42, "Summarization")

    def test_ece_in_range(self):
        rows = [{"confidence": 0.1, "correct": 0.0},
                {"confidence": 0.4, "correct": 1.0},
                {"confidence": 0.9, "correct": 1.0}] * 10
        e = ece(rows)
        self.assertGreaterEqual(e, 0.0)
        self.assertLessEqual(e, 1.0)

    def test_delta_ece_zero_for_identical(self):
        rows = [{"confidence": 0.5, "correct": 1.0} for _ in range(20)]
        self.assertAlmostEqual(delta_ece(rows, rows), 0.0, places=6)

    def test_bootstrap_ci_in_order(self):
        values = [0.1 * i for i in range(10)]
        mean, low, high = bootstrap_ci(values)
        self.assertLessEqual(low, mean)
        self.assertLessEqual(mean, high)


class CorpusTests(unittest.TestCase):
    def test_corpus_caches(self):
        if CORPUS_PATH.exists():
            CORPUS_PATH.unlink()
        try:
            p1 = load_passages()
            p2 = load_passages()
            self.assertEqual(len(p1), N_PASSAGES)
            self.assertEqual(len(p2), N_PASSAGES)
            # Cached — same ids and same text
            self.assertEqual(p1[0]["passage_id"], p2[0]["passage_id"])
            self.assertEqual(p1[0]["text"], p2[0]["text"])
        finally:
            if CORPUS_PATH.exists():
                CORPUS_PATH.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)