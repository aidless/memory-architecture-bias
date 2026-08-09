#!/usr/bin/env python3
"""_verify_TEMPLATE.py — generic config-driven 6-category TMLR audit.

This is the GENERIC TEMPLATE. To use:

    1. Copy this file to F:/Research/PAPER<N>_CONSOLIDATED/_verify_p<N>.py
    2. Edit the `ROOT` constant.
    3. Edit the `CHECKS_CONFIG` block to match the paper.

Or, run `python gen_verify_scripts.py --paper N` from
F:/Research/TEMPLATE/ to fork this template automatically.

The seven categories of checks are:

  C1  Abstract symbol definitions
      - For each entry in CHECKS_CONFIG['c1_symbols'], verify that the
        abstract contains an inline definitional phrase within a
        250-character window of the first mention.
  C2  Bonferroni scheme consistency
      - Verify that the abstract, body, and table notes are consistent
        with the families declared in CHECKS_CONFIG['c2_families'].
      - Optionally verify that a section matching
        CHECKS_CONFIG['c2_section_pattern'] exists.
  C3  Formalization of a key concept
      - Verify that a concept (declared in CHECKS_CONFIG['c3_concept'])
        has a formal definition (matching CHECKS_CONFIG['c3_formal'])
        before being used qualitatively.
  C4  Citation hygiene (generic)
      - Every \\cite{...} key in main.tex must have a corresponding
        @...{key,...} entry in refs.bib.
      - Self-cite rate must be below the threshold declared in
        CHECKS_CONFIG['c4_self_cite_threshold'].
  C5  Sample size and effect-size transparency (generic)
      - Every p-value reported in the abstract must be paired with n
        and a test name.
      - Every d=... in the abstract must be declared as "Cohen's d"
        (or whichever effect size type is set in CHECKS_CONFIG['c5_d_type']).
  C6  Blacklisted vocabulary (generic)
      - Every word in CHECKS_CONFIG['c6_blacklist'] is flagged for
        replacement.
  C7  Citation context (ceremonial vs engaged) (generic, v0.1.2)
      - For each \\cite{...} in main.tex, classify the citing
        sentence as "engaged" or "ceremonial". A ceremonial
        citation has no engage verb (show, demonstrate, extend,
        build on, ...), no comparison word (however, while, ...),
        and the citing sentence is < 30 words. The check is
        lenient by default: up to c7_max_ceremonial (default 2)
        ceremonial cites are silent; (N+1)+ are reported as
        MED severity.

Exit codes:
    0 = no HIGH-severity findings
    1 = at least one HIGH-severity finding
    2 = I/O error (missing file, etc.)
"""
from __future__ import annotations
import re
import sys
from collections import defaultdict
from pathlib import Path

# ============================================================================
# Configuration (only this block needs editing per paper)
# ============================================================================
ROOT = Path('F:/Research/PAPER5_CONSOLIDATED')
MAIN = ROOT / 'main.tex'
REFS = ROOT / 'refs.bib'

# Each entry in CHECKS_CONFIG controls one of the 6 categories. The check
# functions below read from this dict, so per-paper changes happen entirely
# here — no code edits required.
#
# Schema (see gen_verify_scripts.py for canonical examples):
#   c1_symbols: list of dicts, one per symbol that must be defined in the
#               abstract. Each dict has:
#                 - 'name'         (str): human-readable label
#                 - 'token'        (str): the raw token to search for in the
#                                       abstract (e.g., r'\Gamma', 'CAF',
#                                       'E_T', 'TTRL')
#                 - 'definition'   (str): a regex that must match within
#                                       250 chars of the first mention.
#                 - 'window'       (int, optional): window size in chars
#                                       (default 250)
#
#   c2_families: dict {family_name: k}. The auditor checks that the
#                abstract's k value, if any, is in this set.
#   c2_section_pattern: regex that must match a \\section / \\subsection
#                       title declaring the statistical protocol. Use
#                       r'\\section\*?\{[^}]*Power analysis[^}]*\}|...
#                       to also accept star-form sections.
#   c2_abstract_k_allowed: list[int] of k values that are acceptable in
#                         the abstract. Usually this is the family-level k.
#
#   c3_concept: str label of the concept that must be formally defined
#               (e.g., "crossover", "Two Faces", "impossibility triangle").
#   c3_concept_token: regex matching the concept as it appears in
#                     \\textbf{...} or as a bare word.
#   c3_formal: regex that must appear before the first qualitative use
#              of the concept. For example, the formal definition of a
#              "crossover" is `crossover.{0,80}\\arg\\?min`.
#
#   c4_self_cite_threshold: float, default 0.30. Self-cite rate above
#                          this triggers a finding.
#   c4_self_cite_prefix:   str, default 'liu2026'. Cite key prefix used
#                          to detect self-cites.
#   c4_max_self_cite_keys: int, default 3. Maximum number of self-cite
#                          keys allowed (for method-foundation retention).
#
#   c5_d_type: str, default "Cohen's d". Effect-size type that must be
#              declared in the abstract alongside every d=... value.
#
#   c6_blacklist: list[str] of words to flag. Each word is matched with
#                 case-insensitive word boundaries.
CHECKS_CONFIG: dict = {
    'c1_symbols':
    [
        {
            'name': '$\\Gamma_{\\mathrm{temporal}}$ (Wasserstein-1 bias-propagation metric)',
            'token': '\\\\Gamma',
            'definition': r'\\Gamma_\{\\text\{temporal\}\}\s*=|Wasserstein',
        },
        {
            'name': 'contamination rate (fraction of stored outputs modified)',
            'token': 'contamination rate',
            'definition': 'fraction of stored outputs|proportion of stored|modified at the start',
        },
        {
            'name': 'length bias',
            'token': 'length bias',
            'definition': r'expansion by a factor|expansion factor|output expansion|alpha=1\.5',
        },
        {
            'name': 'authority bias',
            'token': 'authority bias',
            'definition': 'explicit source|source.attribution|"according to',
        },
    ],

    'c2_families':
    {'dose-response': 9, 'cross-model': 6, 'authority-bias': 3},
    'c2_section_pattern': r'\\section\*?\{[^}]*Power analysis[^}]*\}|\\subsection\*?\{[^}]*Statistical Protocol[^}]*\}',
    'c2_abstract_k_allowed': [9],

    'c3_concept': 'crossover',
    'c3_concept_token': r'\\textbf\{crossover\}|\bcrossover\b',
    'c3_formal': 'crossover.{0,80}\\\\arg\\\\?min',
    'c3_formal_secondary': None,

    'c4_self_cite_threshold': 0.3,
    'c4_self_cite_prefix': 'liu2026',
    'c4_max_self_cite_keys': 1,

    'c5_d_type': "Cohen's d",

    'c6_blacklist':
    ['paradigm', 'yield', 'reveal'],
}
# ============================================================================


# Default inflection regexes (override per-word by adding to INFLECTIONS).
DEFAULT_INFLECTIONS = {
    'paradigm': r'\bparadigms?\b',
    'yield':    r'\byields?\b',
    'reveal':   r'\breveals?\b|\brev\b|\brevealed\b',
}


SEVERITY = {
    'C1': 'HIGH',
    'C2': 'HIGH',
    'C3': 'MEDIUM',
    'C4': 'MEDIUM',
    'C5': 'MEDIUM',
    'C6': 'LOW',
    'C7': 'MEDIUM',
    # C10 is variable: HIGH for missing availability, MED for
    # consistency / future-tense, LOW for missing metadata.
    # We default to LOW since most C10 findings are LOW; the
    # function itself emits the per-finding severity in the
    # message.
    'C10': 'LOW',
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def line_of(tex: str, pos: int) -> int:
    return tex.count('\n', 0, pos) + 1


def extract_abstract(tex: str) -> tuple[str, int] | None:
    """Return (abstract_text, abs_start_position) or None if no abstract."""
    m = re.search(r'\\begin\{abstract\}(.+?)\\end\{abstract\}', tex, re.DOTALL)
    if m is None:
        return None
    return m.group(1), m.start(1)


# ---------------------------------------------------------------------------
# C1: Abstract symbol definitions
# ---------------------------------------------------------------------------

def check_c1_abstract_definitions(tex: str) -> list[tuple[str, str, int]]:
    cfg_syms = CHECKS_CONFIG['c1_symbols']
    if not cfg_syms:
        return []

    abs_result = extract_abstract(tex)
    if abs_result is None:
        return [('C1', 'No abstract environment found.', -1)]
    abstract, abs_start = abs_result
    abs_line_start = line_of(tex, abs_start)

    findings: list[tuple[str, str, int]] = []
    for sym in cfg_syms:
        name = sym['name']
        token = sym['token']
        defn = sym['definition']
        window = sym.get('window', 250)
        m = re.search(token, abstract, re.IGNORECASE)
        if not m:
            continue  # symbol not in abstract — fine
        # First pass: definition within `window` chars of first mention.
        win_start = max(0, m.start() - window)
        win_end = min(len(abstract), m.end() + window)
        if re.search(defn, abstract[win_start:win_end], re.IGNORECASE | re.DOTALL):
            continue
        # Second pass: definition anywhere within the abstract (e.g., a
        # "Notation" block at the end of the abstract).
        if re.search(defn, abstract, re.IGNORECASE | re.DOTALL):
            continue
        # Third pass: definition in the first \\section{Introduction}
        # that immediately follows the abstract (a common style choice).
        intro_match = re.search(
            r'\\section\{Introduction\}(.+?)\\section\{',
            tex, re.DOTALL,
        )
        if intro_match and re.search(
            defn, intro_match.group(1), re.IGNORECASE | re.DOTALL,
        ):
            continue
        line_no = abs_line_start + abstract[:m.start()].count('\n')
        findings.append((
            'C1',
            f'{name} appears in abstract without inline definition. '
            f'Reviewer §3 #1.',
            line_no,
        ))
        break  # one finding per abstract is enough

    return findings


# ---------------------------------------------------------------------------
# C2: Bonferroni scheme consistency
# ---------------------------------------------------------------------------

def check_c2_bonferroni_consistency(tex: str) -> list[tuple[str, str, int]]:
    findings: list[tuple[str, str, int]] = []

    families = CHECKS_CONFIG['c2_families']
    section_pat = CHECKS_CONFIG['c2_section_pattern']
    abstract_k_allowed = CHECKS_CONFIG.get('c2_abstract_k_allowed',
                                           sorted(set(families.values())))

    # Check whether the declared section exists
    if section_pat and not re.search(section_pat, tex):
        findings.append((
            'C2',
            'No Power analysis section declaring Bonferroni k found. '
            'Reviewer §3 #4.',
            -1,
        ))

    # Check the abstract for k=N mention
    abs_result = extract_abstract(tex)
    if abs_result:
        abstract, abs_start = abs_result
        abstract_k = re.search(r'Bonferroni[^.]*?k\s*=\s*(\d+)', abstract)
        if abstract_k:
            k_val = int(abstract_k.group(1))
            if k_val not in abstract_k_allowed:
                abs_line_start = line_of(tex, abs_start)
                line_in_abs = abstract[:abstract_k.start()].count('\n')
                findings.append((
                    'C2',
                    f'Abstract quotes Bonferroni k={k_val} but the '
                    f'authoritative scheme has k values '
                    f'{sorted(set(families.values()))}. The abstract must '
                    f'quote the family-level correction; otherwise readers '
                    f'are misled. Reviewer §4 #1.',
                    abs_line_start + line_in_abs,
                ))

    return findings


# ---------------------------------------------------------------------------
# C3: Formalization of a key concept
# ---------------------------------------------------------------------------

def check_c3_formalization(tex: str) -> list[tuple[str, str, int]]:
    findings: list[tuple[str, str, int]] = []

    concept = CHECKS_CONFIG.get('c3_concept')
    concept_token = CHECKS_CONFIG.get('c3_concept_token')
    formal_pat = CHECKS_CONFIG.get('c3_formal')
    formal_secondary = CHECKS_CONFIG.get('c3_formal_secondary')

    if not concept_token or not formal_pat:
        return findings

    m = re.search(concept_token, tex)
    if not m:
        return findings
    first_line = line_of(tex, m.start())

    if not re.search(formal_pat, tex, re.IGNORECASE | re.DOTALL):
        findings.append((
            'C3',
            f'"{concept}" is used but no formal definition matching '
            f'{formal_pat!r} is given. Reviewer §3 #2.',
            first_line,
        ))

    if formal_secondary and not re.search(formal_secondary, tex,
                                          re.IGNORECASE | re.DOTALL):
        findings.append((
            'C3',
            f'"{concept}" second-half formal definition matching '
            f'{formal_secondary!r} not found. Reviewer §3 #2.',
            first_line,
        ))

    return findings


# ---------------------------------------------------------------------------
# C4: Citation hygiene (generic)
# ---------------------------------------------------------------------------

def check_c4_citation_hygiene(tex: str, bib: str) -> list[tuple[str, str, int]]:
    findings: list[tuple[str, str, int]] = []

    cite_keys: list[str] = []
    for m in re.finditer(r'\\cite[a-zA-Z]*\{([^}]+)\}', tex):
        for k in m.group(1).split(','):
            k = k.strip()
            if k and not any(c in k for c in '$&'):
                cite_keys.append(k)

    bib_keys = set(re.findall(r'@\w+\{([^,]+),', bib))
    cited_keys = set(cite_keys)

    missing = cited_keys - bib_keys
    if missing:
        first_missing_line = -1
        for k in sorted(missing):
            m = re.search(r'\\cite[a-zA-Z]*\{[^}]*\b' + re.escape(k) + r'\b', tex)
            if m:
                ln = line_of(tex, m.start())
                if first_missing_line < 0 or ln < first_missing_line:
                    first_missing_line = ln
        findings.append((
            'C4',
            f'{len(missing)} cite key(s) in main.tex missing from refs.bib: '
            f'{sorted(missing)[:5]}{"..." if len(missing) > 5 else ""}',
            first_missing_line,
        ))

    # Self-citation hygiene
    threshold = CHECKS_CONFIG['c4_self_cite_threshold']
    prefix = CHECKS_CONFIG['c4_self_cite_prefix']
    max_keys = CHECKS_CONFIG['c4_max_self_cite_keys']
    self_cites = sorted(k for k in cited_keys if k.lower().startswith(prefix))
    if self_cites:
        rate = len(self_cites) / len(cited_keys) if cited_keys else 0
        if len(self_cites) > max_keys or rate >= threshold:
            findings.append((
                'C4',
                f'Self-cite keys present: {self_cites} '
                f'({len(self_cites)}/{len(cited_keys)} = {rate:.1%}). '
                f'Target: <{threshold:.0%} key-level; max {max_keys} keys '
                f'for method-foundation retention.',
                -1,
            ))

    return findings


# ---------------------------------------------------------------------------
# C5: Sample size and effect-size transparency (generic)
# ---------------------------------------------------------------------------

def check_c5_sample_size_and_test(tex: str) -> list[tuple[str, str, int]]:
    findings: list[tuple[str, str, int]] = []

    abs_result = extract_abstract(tex)
    if abs_result is None:
        return findings
    abstract, abs_start = abs_result
    abs_line_start = line_of(tex, abs_start)

    # Helper: where do n, N, and test names appear?  We accept three
    # sources: (a) within 250 chars of the p-value in the abstract,
    # (b) anywhere else in the abstract (Notation block at end), and
    # (c) in the first \\section{Introduction} that immediately follows.
    intro_match = re.search(
        r'\\section\{Introduction\}(.+?)\\section\{', tex, re.DOTALL,
    )
    intro_section = intro_match.group(1) if intro_match else ''

    def _has_n_and_test(window: str) -> tuple[bool, bool]:
        has_n = bool(re.search(
            r'n\s*=\s*\d+|N\s*=\s*\d+|seeds?|conditions?',
            window, re.IGNORECASE,
        ))
        # Note: the test-name pattern intentionally allows arbitrary
        # non-letter characters between "paired" and "t", between "t"
        # and "test", and uses "test[s]?" to allow "tests" plural. This
        # matches "paired $t$-test", "paired $t$-tests", "paired\\s+t-test",
        # "paired t-tests", etc.
        has_test = bool(re.search(
            r'(Wilcoxon|'
            r'paired[^a-zA-Z]{0,8}t[^a-zA-Z]{0,3}test|'
            r'\bt[^a-zA-Z]{0,3}test|'
            r'Mann.Whitney|permutation)',
            window, re.IGNORECASE,
        ))
        return has_n, has_test

    # p-values in abstract
    p_patterns = (
        re.compile(r'p\s*<\s*0\.0+\d+'),
        re.compile(r'p_\\text\{adj\}|p\\text\{adj\}'),
    )
    for pat in p_patterns:
        for m in pat.finditer(abstract):
            line_in_abs = abstract[:m.start()].count('\n')
            line_no = abs_line_start + line_in_abs
            win_start = max(0, m.start() - 250)
            win_end = min(len(abstract), m.end() + 50)
            has_n, has_test = _has_n_and_test(abstract[win_start:win_end])
            if not (has_n and has_test):
                # Second pass: check the entire abstract.
                has_n_b, has_test_b = _has_n_and_test(abstract)
                if has_n_b:
                    has_n = True
                if has_test_b:
                    has_test = True
            if not (has_n and has_test) and intro_section:
                # Third pass: check the intro section.
                has_n_i, has_test_i = _has_n_and_test(intro_section)
                if has_n_i:
                    has_n = True
                if has_test_i:
                    has_test = True
            if not (has_n and has_test):
                missing = []
                if not has_n:
                    missing.append('n (sample size) or seeds/conditions qualifier')
                if not has_test:
                    missing.append('test name')
                findings.append((
                    'C5',
                    f'Reported p-value at abstract line {line_no} is missing '
                    f'{", ".join(missing)}. Reviewer §4 #1.',
                    line_no,
                ))

    # d= in abstract
    d_type = CHECKS_CONFIG.get('c5_d_type', "Cohen's d")
    d_pattern = re.compile(r'd\s*=\s*[\d.]+')
    for m in d_pattern.finditer(abstract):
        line_in_abs = abstract[:m.start()].count('\n')
        line_no = abs_line_start + line_in_abs
        win_start = max(0, m.start() - 150)
        win_end = min(len(abstract), m.end() + 50)
        if re.search(re.escape(d_type.split()[0]),
                     abstract[win_start:win_end], re.IGNORECASE):
            continue
        if re.search(re.escape(d_type.split()[0]), abstract, re.IGNORECASE):
            continue
        if intro_section and re.search(
            re.escape(d_type.split()[0]), intro_section, re.IGNORECASE,
        ):
            continue
        findings.append((
            'C5',
            f'Effect size d=... at abstract line {line_no} does not '
            f'explicitly declare "{d_type}". Reviewer §4 #1.',
            line_no,
        ))

    return findings


# ---------------------------------------------------------------------------
# C6: Blacklisted vocabulary (generic)
# ---------------------------------------------------------------------------

def check_c6_blacklist(tex: str) -> list[tuple[str, str, int]]:
    findings: list[tuple[str, str, int]] = []
    counts: dict[str, int] = defaultdict(int)
    samples: dict[str, list[tuple[int, str]]] = defaultdict(list)

    # Minimum occurrences before a blacklist word is reported.
    # 1-2 occurrences of "yield" / "reveal" is common in
    # idiomatic technical English ("yields a value of X")
    # and does not indicate vague writing. 3+ is the
    # threshold for "this word is being over-used to avoid
    # saying something specific".
    min_count: int = 3

    blacklist = CHECKS_CONFIG.get('c6_blacklist', [])
    for word in blacklist:
        pattern = DEFAULT_INFLECTIONS.get(word, rf'\b{word}\b')
        for m in re.finditer(pattern, tex, re.IGNORECASE):
            counts[word] += 1
            if len(samples[word]) < 3:
                ln = line_of(tex, m.start())
                samples[word].append((ln, word))

    for word, n in sorted(counts.items()):
        if n < min_count:
            continue  # 1-2 occurrences are OK
        first_line = samples[word][0][0] if samples[word] else -1
        findings.append((
            'C6',
            f'Blacklist word "{word}" appears {n}x in main.tex '
            f'(e.g., line {first_line}). Reviewer §5 #5.',
            first_line,
        ))

    return findings


# ---------------------------------------------------------------------------
# C7: Citation context (ceremonial vs engaged)
# ---------------------------------------------------------------------------
#
# A citation is "ceremonial" if it appears in the text but the
# citing sentence does not actually engage with the cited work.
# Reviewers notice this and dock the paper for it. The check
# detects citations whose citing sentence has no engagement
# signal (no engage verb, no comparison word, short sentence).
#
# Engagement signals (a sentence is "engaged" if ANY of these hold):
#   1. contains an engage verb (show, demonstrate, extend, ...)
#   2. contains a comparison word (however, in contrast, while, ...)
#   3. is 30+ words long (elaboration = engagement by length)
#
# Per-paper threshold (c7_max_ceremonial, default 2):
#   0 = strict (every ceremonial cite flagged)
#   1 = one ceremonial OK, two+ flagged
#   2 = up to two ceremonial OK, three+ flagged
#
# Severity: MEDIUM (stylistic, not correctness).
# ---------------------------------------------------------------------------

# Engagement signals (lowercase, matched as substrings).
_C7_ENGAGE_VERBS = (
    'show', 'shows', 'showed', 'demonstrate', 'demonstrates',
    'demonstrated', 'extend', 'extends', 'extended',
    'build on', 'builds on', 'built on', 'follow', 'follows',
    'followed', 'use', 'uses', 'used', 'apply', 'applies',
    'applied', 'compare', 'compares', 'compared',
    'improve', 'improves', 'improved', 'outperform',
    'outperforms', 'outperformed', 'validate', 'validates',
    'validated', 'verify', 'verifies', 'verified',
    'propose', 'proposes', 'proposed', 'argue', 'argues',
    'argued', 'claim', 'claims', 'claimed',
    'find', 'finds', 'found', 'observe', 'observes', 'observed',
    'measure', 'measures', 'measured', 'report', 'reports',
    'reported', 'confirm', 'confirms', 'confirmed',
    'exploit', 'exploits', 'exploited',
    'leverage', 'leverages', 'leveraged',
    'utilize', 'utilizes', 'utilized',
    'adopt', 'adopts', 'adopted',
    'generalize', 'generalizes', 'generalized',
    'specialize', 'specializes', 'specialized',
    'reduce', 'reduces', 'reduced',
    'combine', 'combines', 'combined',
    'investigate', 'investigates', 'investigated',
    'analyze', 'analyzes', 'analyzed', 'analysis',
    'examine', 'examines', 'examined',
    'introduce', 'introduces', 'introduced',
    'present', 'presents', 'presented',
    'derive', 'derives', 'derived',
    'compute', 'computes', 'computed',
)

_C7_COMPARISON_WORDS = (
    'however', 'in contrast', 'unlike', 'while',
    'although', 'whereas', 'but ', 'conversely',
    'on the other hand', 'nevertheless', 'nonetheless',
)

_C7_MIN_CITED_SENTENCE_WORDS = 30


def _c7_extract_sentence(tex: str, pos: int) -> str:
    r"""Extract the sentence containing position ``pos`` in ``tex``.

    A "sentence" is the text between the nearest sentence-end
    punctuation (`. `, `! `, `? `, `.\n`, `!\\n`, `?\\n`) before
    pos and the nearest one after pos. Periods that are part of
    common abbreviations (e.g., "et al.", "e.g.", "i.e.") are
    NOT treated as sentence boundaries.

    To handle the common LaTeX pattern where the cite is at the
    END of a sentence (after the engagement verb), the function
    returns up to TWO sentences: the current sentence plus the
    previous one. This way, a sentence like

        We extend Smith et al. \cite{smith2020} by ...

    is correctly identified as engaged (because "extend" is in
    the previous sentence).
    """
    sentence_end_re = re.compile(r'[.!?](?:\s|\n)')

    # Find all sentence-end positions.
    ends = [m.end() for m in sentence_end_re.finditer(tex)]

    # The end of the current sentence is the smallest end > pos.
    end_idx = None
    for i, e in enumerate(ends):
        if e > pos:
            end_idx = i
            break
    if end_idx is None:
        end = len(tex)
    else:
        end = ends[end_idx]

    # The start of the current sentence is the largest end <= pos.
    # If end_idx is 0, the start is 0. Otherwise it's ends[end_idx - 1].
    if end_idx is None or end_idx == 0:
        start = 0
        # No previous sentence.
        return tex[start:end]

    # Otherwise, start at the previous sentence boundary.
    start = ends[end_idx - 1]

    return tex[start:end]


def _c7_is_engaged(sentence: str) -> bool:
    """True if ``sentence`` engages with the cited work.

    Engagement is any of:
      1. an engage verb (substring match, case-insensitive)
      2. a comparison word (substring match, case-insensitive)
      3. sentence is 30+ words long (elaboration heuristic)
    """
    s = sentence.lower()
    for verb in _C7_ENGAGE_VERBS:
        if verb in s:
            return True
    for comp in _C7_COMPARISON_WORDS:
        if comp in s:
            return True
    if len(s.split()) >= _C7_MIN_CITED_SENTENCE_WORDS:
        return True
    return False


def check_c7_citation_context(
    tex: str,
    c7_max_ceremonial: int = 2,
    c7_llm_budget: int = 0,
) -> list[tuple[str, str, int]]:
    """C7: detect ceremonial citations (cited but not engaged with).

    A citation is "ceremonial" if the citing sentence does not
    engage with the cited work (no engage verb, no comparison
    word, short sentence). The check is **lenient** by default:
    1-2 ceremonial cites are OK; only 3+ ceremonial cites
    produce a finding. Set c7_max_ceremonial=0 for strict mode
    (every ceremonial cite is flagged).

    The optional `c7_llm_budget` parameter enables an LLM-based
    second opinion for **borderline** ceremonial cites (citing
    sentences that are 20-30 words long). When the LLM
    says "engaged", the cite is demoted (removed from the
    ceremonial set). When it says "ceremonial", the cite
    is confirmed. The LLM fallback is opt-in: set
    c7_llm_budget > 0 AND the TMAUDIT_LLM_ENDPOINT and
    TMAUDIT_LLM_API_KEY env vars to enable. See
    `src/tmaudit/llm_fallback.py` for details.

    Returns:
        0 or 1 finding of the form:
            ('C7', 'MED: <N> ceremonial citation(s) ...', first_line)
        The finding message includes the threshold, the count of
        ceremonial cites, and the first 5 keys (sorted).

    Acceptance criteria:
      - Per-cite classification (engaged vs ceremonial) is
        correct (see tests/test_c7_citation_context.py).
      - Per-paper threshold (c7_max_ceremonial) is respected.
      - All cite variants (\\cite, \\citep, \\citet) are detected.
      - Multi-key cites (\\cite{a,b,c}) are counted per key.
      - Unique keys are counted, not occurrences.
    """
    findings: list[tuple[str, str, int]] = []

    # The threshold is taken from the function argument (caller
    # decides). The per-paper CHECKS_CONFIG['c7_max_ceremonial'] is
    # NOT used here because it would override the function arg,
    # which the unit tests rely on. The driver (main) is
    # responsible for reading CHECKS_CONFIG and passing it as the
    # function arg.

    # 1. Find all \cite{...} matches and classify each citing sentence.
    ceremonial_keys: dict[str, int] = {}  # key -> first line
    all_cited_keys: set[str] = set()

    for m in re.finditer(r'\\cite[a-zA-Z]*\{([^}]+)\}', tex):
        for k in m.group(1).split(','):
            k = k.strip()
            if not k or any(c in k for c in '$&'):
                continue
            all_cited_keys.add(k)
            # Extract the citing sentence.
            sentence = _c7_extract_sentence(tex, m.start())
            if not _c7_is_engaged(sentence):
                ln = line_of(tex, m.start())
                # Count unique keys, not occurrences.
                if k not in ceremonial_keys:
                    ceremonial_keys[k] = ln

    # 1b. (v0.2.0) Optional LLM-based second opinion for
    # BORDERLINE ceremonial cites. A sentence is "borderline"
    # if it's 20-30 words long and the heuristic marked it
    # as ceremonial. For these cases, the heuristic is
    # most likely to be wrong, so we ask an LLM for
    # confirmation.
    #
    # The fallback is opt-in: it makes zero LLM calls unless
    # the user has set TMAUDIT_LLM_* env vars and the driver
    # has passed c7_llm_budget > 0.
    if c7_llm_budget > 0:
        try:
            from .. import llm_fallback as _llm
            fb = _llm.LLMFallback(budget=c7_llm_budget)
            if fb.is_enabled():
                # Collect borderline cites with their sentences.
                # We need to re-extract the sentence for each
                # ceremonial cite.
                borderline_to_recheck: list[str] = []
                for k, ln in ceremonial_keys.items():
                    # Find a cite with this key (use first match)
                    for m2 in re.finditer(
                        r'\\cite[a-zA-Z]*\{[^}]*\b' + re.escape(k) + r'\b[^}]*\}',
                        tex,
                    ):
                        sentence = _c7_extract_sentence(tex, m2.start())
                        if _llm.is_borderline(sentence):
                            borderline_to_recheck.append((k, sentence))
                        break  # only first match per key
                # Re-check each borderline cite
                for k, sentence in borderline_to_recheck:
                    try:
                        result = fb.classify(sentence)
                    except _llm.LLMBudgetExceeded:
                        break  # out of budget
                    if result is not None and result.engaged:
                        # LLM says engaged: demote (remove from ceremonial).
                        del ceremonial_keys[k]
        except ImportError:
            pass  # llm_fallback module not available

    # 2. Report per-ceremonial-cite findings, but only if count
    # exceeds the threshold. Up to `c7_max_ceremonial` ceremonial
    # cites are silently OK (default 2); (N+1)+ ceremonial cites
    # each get a per-cite finding.
    n_ceremonial = len(ceremonial_keys)
    if n_ceremonial > c7_max_ceremonial:
        # Per-cite findings (sorted by line, then key for stability).
        sorted_keys = sorted(
            ceremonial_keys.items(), key=lambda kv: (kv[1], kv[0])
        )
        # Only report the (N+1)+ ceremonial cites that exceed
        # the threshold. The first N are silent.
        excess = sorted_keys[c7_max_ceremonial:]
        for k, ln in excess:
            findings.append((
                'C7',
                f'MED: citation {k!r} at line {ln} is ceremonial '
                f'(citing sentence does not engage with the cited '
                f'work: no engage verb, no comparison, no '
                f'elaboration >= {_C7_MIN_CITED_SENTENCE_WORDS} '
                f'words). {n_ceremonial} ceremonial cite(s) total '
                f'(threshold: {c7_max_ceremonial}). Reviewer §5 #6.',
                ln,
            ))

    return findings


# ---------------------------------------------------------------------------
# C10: Reproducibility (added in v0.3.0)
# ---------------------------------------------------------------------------
#
# A paper's reproducibility is judged on 3 sub-categories:
#   1. Availability statement: does the paper say where the
#      code/data can be obtained?
#   2. Statement consistency: if the paper claims "we achieve
#      SOTA on dataset X" but the availability statement says
#      "we do not release", that's a real reviewer concern.
#   3. Reproducibility metadata: hyperparameters, random seed,
#      hardware, library version.
#
# Severity:
#   HIGH: no availability statement at all.
#   MED:  consistency issue or future-tense release.
#   LOW:  one or more metadata categories missing.
#
# The check is opt-in via the per-paper c10_reproducibility_claims
# config. If the config is empty/None, only the availability
# and metadata checks run (the consistency check is skipped).
# ---------------------------------------------------------------------------

# Regex patterns for the availability statement.
_C10_AVAILABILITY_SECTION_RE = re.compile(
    r'\\section\*?\{[^}]*Availability[^}]*\}',
    re.IGNORECASE,
)
# URLs pointing to known code/data hosting sites.
_C10_AVAILABILITY_URL_RES = [
    re.compile(r'github\.com/[^\s\)\}\]]+', re.IGNORECASE),
    re.compile(r'gitlab\.com/[^\s\)\}\]]+', re.IGNORECASE),
    re.compile(r'huggingface\.co/[^\s\)\}\]]+', re.IGNORECASE),
    re.compile(r'doi\.org/[^\s\)\}\]]+', re.IGNORECASE),
    re.compile(r'dx\.doi\.org/[^\s\)\}\]]+', re.IGNORECASE),
    re.compile(r'zenodo\.org/[^\s\)\}\]]+', re.IGNORECASE),
    re.compile(r'anonymous\.4open\.science/[^\s\)\}\]]+', re.IGNORECASE),
    re.compile(r'openreview\.net/[^\s\)\}\]]+', re.IGNORECASE),
]
# Phrases indicating a release statement.
_C10_AVAILABILITY_PHRASE_RES = [
    re.compile(r'code\s+is\s+available\s+at', re.IGNORECASE),
    re.compile(r'data\s+is\s+available\s+at', re.IGNORECASE),
    re.compile(r'source\s+code\s+is\s+released', re.IGNORECASE),
    re.compile(r'we\s+release\s+', re.IGNORECASE),
    re.compile(r'we\s+make\s+available', re.IGNORECASE),
    re.compile(r'publicly\s+available', re.IGNORECASE),
    re.compile(r'open[\s\-]source', re.IGNORECASE),
]
# Phrases indicating NO release (used for consistency check).
_C10_NO_RELEASE_PHRASE_RES = [
    re.compile(r'we\s+do\s+not\s+release', re.IGNORECASE),
    re.compile(r'will\s+not\s+release', re.IGNORECASE),
    re.compile(r'not\s+publicly\s+available', re.IGNORECASE),
    re.compile(r'proprietary\s+restrictions', re.IGNORECASE),
    re.compile(r'cannot\s+be\s+released', re.IGNORECASE),
]
# Phrases indicating future-tense release.
_C10_FUTURE_TENSE_RES = [
    re.compile(r'we\s+will\s+release', re.IGNORECASE),
    re.compile(r'we\s+plan\s+to\s+release', re.IGNORECASE),
    re.compile(r'will\s+be\s+released', re.IGNORECASE),
    re.compile(r'upon\s+(?:paper\s+)?acceptance', re.IGNORECASE),
]

# Reproducibility metadata patterns.
# Each is a (pattern, label) tuple. The label is used in
# the LOW finding message.
_C10_HYPERPARAM_PATTERNS = [
    re.compile(r'\blearning[\s_]rate\b', re.IGNORECASE),
    re.compile(r'\bbatch[\s_]size\b', re.IGNORECASE),
    re.compile(r'\boptimizer\b', re.IGNORECASE),
    re.compile(r'\bepochs?\b', re.IGNORECASE),
    re.compile(r'\blearning[\s_]rate[\s=]+\d', re.IGNORECASE),
]
_C10_SEED_PATTERNS = [
    re.compile(r'\brandom[\s_]seed\b', re.IGNORECASE),
    re.compile(r'\bseed[\s=]+\d', re.IGNORECASE),
    re.compile(r'torch\.manual_seed', re.IGNORECASE),
    re.compile(r'np\.random\.seed', re.IGNORECASE),
    re.compile(r'\bset[\s_]seed\(', re.IGNORECASE),
]
_C10_HARDWARE_PATTERNS = [
    re.compile(r'\bGPU\b'),
    re.compile(r'\bRTX[\s\-]?\d{4}', re.IGNORECASE),
    re.compile(r'\bA\d{2,4}\b'),  # A100, A1000, etc.
    re.compile(r'\bV\d{2,4}\b'),  # V100, V1000, etc.
    re.compile(r'\bT\d{1,2}\b'),   # T4, T40, etc.
    re.compile(r'\bTesla\s+[A-Z]?\d+', re.IGNORECASE),
    re.compile(r'\bH\d{2}\b'),     # H100, H200
    re.compile(r'\bnvidia[\s\-]?tesla\b', re.IGNORECASE),
    re.compile(r'\bcuda\b', re.IGNORECASE),
]
_C10_LIBRARY_VERSION_PATTERNS = [
    re.compile(r'PyTorch\s+\d', re.IGNORECASE),
    re.compile(r'TensorFlow\s+\d', re.IGNORECASE),
    re.compile(r'transformers\s+\d', re.IGNORECASE),
    re.compile(r'pytorch\s+\d', re.IGNORECASE),
    re.compile(r'tensorflow\s+\d', re.IGNORECASE),
    re.compile(r'scikit[\s\-]learn\s+\d', re.IGNORECASE),
    re.compile(r'pandas\s+\d', re.IGNORECASE),
    re.compile(r'numpy\s+\d', re.IGNORECASE),
    re.compile(r'CUDA\s+\d', re.IGNORECASE),
]


def _c10_has_availability_statement(tex: str) -> bool:
    """Return True if tex contains any of the availability patterns."""
    if _C10_AVAILABILITY_SECTION_RE.search(tex):
        return True
    for pat in _C10_AVAILABILITY_URL_RES:
        if pat.search(tex):
            return True
    for pat in _C10_AVAILABILITY_PHRASE_RES:
        if pat.search(tex):
            return True
    return False


def _c10_has_no_release_phrase(tex: str) -> bool:
    """Return True if tex says 'we do not release' (or similar)."""
    for pat in _C10_NO_RELEASE_PHRASE_RES:
        if pat.search(tex):
            return True
    return False


def _c10_has_future_tense_release(tex: str) -> bool:
    """Return True if tex says 'we will release' (or similar)."""
    for pat in _C10_FUTURE_TENSE_RES:
        if pat.search(tex):
            return True
    return False


def _c10_has_metadata(pattern_list, tex: str) -> bool:
    """Return True if any pattern in the list matches in tex."""
    for pat in pattern_list:
        if pat.search(tex):
            return True
    return False


def check_c10_reproducibility(
    tex: str,
    c10_reproducibility_claims: list = None,
) -> list[tuple[str, str, int]]:
    """C10: detect missing or inconsistent reproducibility info.

    Sub-check 1: Availability statement
      - If no \\section{...Availability...}, no GitHub/GitLab/
        Zenodo/anonymous URL, and no "code is available" phrase:
        emit HIGH finding.
      - If a future-tense release ("we will release",
        "upon acceptance"): emit MED finding (the release is
        conditional, not a real release).

    Sub-check 2: Statement consistency
      - For each entry in c10_reproducibility_claims:
        - If the body makes a "SOTA" or "state-of-the-art" claim
          and the availability statement says "we do not release":
          emit MED finding (inconsistency).
      - This sub-check is SKIPPED if c10_reproducibility_claims
        is None or empty.

    Sub-check 3: Reproducibility metadata
      - For each missing category (hyperparameters, random seed,
        hardware, library version): emit LOW finding.

    Severity:
      - HIGH: no availability statement at all
      - MED:  consistency issue or future-tense release
      - LOW:  missing metadata category

    Returns:
        A list of (category, message, line) tuples, one per
        finding. Lines are -1 for global findings, positive
        integers for findings tied to a specific source line.
    """
    findings = []
    c10_claims = c10_reproducibility_claims or []

    # Sub-check 1: Availability statement exists
    has_availability = _c10_has_availability_statement(tex)
    if not has_availability:
        # No availability statement at all -> HIGH
        findings.append((
            'C10',
            'HIGH: paper has no code/data availability statement '
            '(no \\section{...Availability...}, no GitHub/GitLab/Zenodo '
            'URL, and no "code is available" phrase). Reviewer §5 #10.',
            -1,
        ))
    else:
        # Has a statement, but is it future-tense? -> MED
        if _c10_has_future_tense_release(tex):
            findings.append((
                'C10',
                'MED: availability statement uses future tense '
                '("we will release" or "upon acceptance"). The release '
                'is conditional, not a real release. Reviewer §5 #10.',
                -1,
            ))

    # Sub-check 2: Statement consistency with claims
    # Only run if c10_claims is non-empty.
    if c10_claims:
        for claim in c10_claims:
            claim_type = claim.get('type', '')
            if claim_type == 'claims_sota':
                # Check if the paper claims SOTA and the statement
                # says "we do not release".
                # First, find a SOTA claim in the body.
                sota_pat = re.compile(
                    r'(state[\s\-]of[\s\-]the[\s\-]art|SOTA|best[\s\-]in[\s\-]class)',
                    re.IGNORECASE,
                )
                sota_match = sota_pat.search(tex)
                if sota_match and _c10_has_no_release_phrase(tex):
                    ln = line_of(tex, sota_match.start())
                    findings.append((
                        'C10',
                        f'MED: paper claims SOTA (line {ln}) but the '
                        f'availability statement says "we do not release". '
                        f'This is an inconsistency: a SOTA claim should be '
                        f'verifiable. Reviewer §5 #10.',
                        ln,
                    ))

    # Sub-check 3: Reproducibility metadata
    has_hyperparams = _c10_has_metadata(_C10_HYPERPARAM_PATTERNS, tex)
    has_seed = _c10_has_metadata(_C10_SEED_PATTERNS, tex)
    has_hardware = _c10_has_metadata(_C10_HARDWARE_PATTERNS, tex)
    has_lib_version = _c10_has_metadata(_C10_LIBRARY_VERSION_PATTERNS, tex)

    if not has_hyperparams:
        findings.append((
            'C10',
            'LOW: no hyperparameters reported (no "learning rate", '
            '"batch size", or "optimizer" found). Reviewer §5 #10.',
            -1,
        ))
    if not has_seed:
        findings.append((
            'C10',
            'LOW: no random seed reported (no "random seed" or '
            '"torch.manual_seed" found). Reviewer §5 #10.',
            -1,
        ))
    if not has_hardware:
        findings.append((
            'C10',
            'LOW: no hardware specs reported (no "GPU", "RTX", "A100", '
            'or "T4" found). Reviewer §5 #10.',
            -1,
        ))
    if not has_lib_version:
        findings.append((
            'C10',
            'LOW: no library version reported (no "PyTorch 2", '
            '"TensorFlow 2", or "transformers 4" found). Reviewer §5 #10.',
            -1,
        ))

    return findings


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> int:
    if not MAIN.exists() or not REFS.exists():
        print(f'ERROR: missing {MAIN} or {REFS}', file=sys.stderr)
        return 2

    tex = read(MAIN)
    bib = read(REFS)

    all_findings: list[tuple[str, str, int]] = []
    all_findings += check_c1_abstract_definitions(tex)
    all_findings += check_c2_bonferroni_consistency(tex)
    all_findings += check_c3_formalization(tex)
    all_findings += check_c4_citation_hygiene(tex, bib)
    all_findings += check_c5_sample_size_and_test(tex)
    all_findings += check_c6_blacklist(tex)
    # C7: read the per-paper threshold from CHECKS_CONFIG.
    c7_threshold = int(CHECKS_CONFIG.get('c7_max_ceremonial', 2))
    all_findings += check_c7_citation_context(tex, c7_max_ceremonial=c7_threshold)
    # C10 (added in v0.3.0): reproducibility audit. Uses
    # the per-paper c10_reproducibility_claims config.
    c10_claims = CHECKS_CONFIG.get('c10_reproducibility_claims', []) or []
    all_findings += check_c10_reproducibility(tex, c10_claims)

    summary = {k: 0 for k in SEVERITY}
    for cat, _, _ in all_findings:
        summary[cat] += 1

    print('=' * 72)
    print(f'PAPER AUDIT  ({Path(__file__).name})')
    print('=' * 72)
    print(f'Source: {MAIN}')
    print(f'Size:   {len(tex):,} chars')
    bib_key_count = len(set(re.findall(r'@\w+\{([^,]+),', bib)))
    print(f'Refs:   {bib_key_count} entries in refs.bib')
    print()
    print('Findings by category:')
    for cat in ('C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C10'):
        sev = SEVERITY[cat]
        n = summary[cat]
        marker = '[OK]' if n == 0 else f'[{sev}]'
        print(f'  {cat}  {marker:7s}  {n} finding(s)')
    print()

    sev_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    all_findings.sort(
        key=lambda x: (sev_order[SEVERITY[x[0]]], x[0], x[2] if x[2] > 0 else 99999)
    )

    if not all_findings:
        print('All checks passed.  No issues detected.')
        return 0

    print('-' * 72)
    print('DETAILED FINDINGS')
    print('-' * 72)
    for cat, msg, line in all_findings:
        sev = SEVERITY[cat]
        loc = f'line {line}' if line > 0 else 'global'
        print(f'\n[{sev}] {cat}  ({loc})')
        for m in msg.splitlines():
            print(f'    {m}')

    print()
    print('=' * 72)
    print(f'TOTAL: {len(all_findings)} findings '
          f'(HIGH={sum(summary[c] for c in summary if SEVERITY[c] == "HIGH")}, '
          f'MEDIUM={sum(summary[c] for c in summary if SEVERITY[c] == "MEDIUM")}, '
          f'LOW={sum(summary[c] for c in summary if SEVERITY[c] == "LOW")})')
    print('=' * 72)

    return 1 if any(SEVERITY[c] == 'HIGH' for c, _, _ in all_findings) else 0


if __name__ == '__main__':
    sys.exit(main())