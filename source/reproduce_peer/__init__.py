"""reproduce_peer — reproducibility harness for PAPER5.

This package exposes the entry points named in
`PAPER5_CONSOLIDATED/protocol.md` so that an independent reproducer can
re-run the experiments and regenerate Tables 2-6 plus Figures 1-3 of
``main.tex`` without consulting the original codebase.

Entry points
------------
- ``seed_lock.seed_for``         — deterministic seed derivation (protocol §7)
- ``config_loader.load_config``  — pin model aliases, endpoints, rate limits
- ``condition_registry.CONDITIONS`` — canonical condition table (protocol §1)
- ``load_corpus.load_passages``  — 30-passage corpus sampler (protocol §4.7)

The heavy I/O (LLM calls, summarizer calls, ECE computation) is delegated
to the scripts under ``tmp/windows/w1-paper5/`` (Qwen n=10 live harness,
DeepSeek authority parallel harness). Those scripts were written before
this package was created; their logic matches the spec here but the
package is the single source of truth going forward.
"""
from .seed_lock import seed_for
from .condition_registry import CONDITIONS, CONDITION_GROUPS

__all__ = ["seed_for", "CONDITIONS", "CONDITION_GROUPS"]
__version__ = "1.0.0"