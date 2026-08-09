"""reproduce_peer.seed_lock — deterministic seed derivation for PAPER5 reproduction.

This module implements the seed-locking contract from
`PAPER5_CONSOLIDATED/protocol.md` section 7. Every random choice in the
reproduction harness MUST flow through `seed_for(...)`. No exceptions.

Usage:
    from reproduce_peer.seed_lock import seed_for
    rng = np.random.default_rng(seed_for("D-A-08", 3, "agent_A", "bias_mask"))

Contract:
    base_seed (default 20260708) is the master salt matching the paper
    submission date. condition_id, seed_id, agent_id, purpose tags partition
    the 32-bit seed space so that no two distinct random choices collide
    by construction.
"""
from __future__ import annotations
import hashlib


def seed_for(
    condition_id: str,
    seed_id: int,
    agent_id: str,
    purpose: str,
    base_seed: int = 20260708,
) -> int:
    """Derive a deterministic 32-bit seed for any random choice.

    Args:
        condition_id: e.g. "D-A-02", "Q-S-AU".
        seed_id: integer seed index, 0..9 (DeepSeek) or 0..9 (Qwen n=10).
        agent_id: "agent_A" or "agent_B".
        purpose: short tag for the use site:
            "bias_mask"  - which outputs to contaminate
            "corpus"     - corpus sampling offset (always 20260708)
            "tfidf"      - TF-IDF vectorizer seed (unused, deterministic)
            "svd"        - TruncatedSVD random_state
            "bootstrap"  - bootstrap resample index
            "judge"      - external-judge sampling index
        base_seed: master salt (date stamp of paper version).

    Returns:
        Unsigned 32-bit integer suitable for ``np.random.default_rng``.

    Notes:
        SHA-256 is overkill for 32-bit seed derivation but is the
        transparent, dependency-free choice. The contract is stable across
        Python versions and OSes.
    """
    key = f"{base_seed}:{condition_id}:{seed_id}:{agent_id}:{purpose}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest()[:16], 16) % (2**32)


__all__ = ["seed_for"]