# Protocol: Reproducing the Three-Architecture Bias-Propagation Experiment

This document specifies the end-to-end reproduction protocol for the experiment
described in `main.tex` of the **Empirical Comparison of Memory Architectures
for Bias-Resistant Multi-Agent LLM Systems** submission. It is written for
`reproduce_peer`: a separate reproducer should be able to run the API calls,
recompute the metrics, and compare the outputs to the paper-level claims.

Code, audit artifacts, and lightweight analysis scripts are referenced at
`https://anonymous.4open.science/r/memory-architecture-bias-F720/` (MIT license). The local
companion implementation should expose `reproduce_peer/seed_lock.py`,
`reproduce_peer/run_protocol.py`, and `scoring/gamma_monitor.py`. **Do not
hard-code API keys in any file** — read them from environment variables
(`DEEPSEEK_API_KEY`, `QWEN_API_KEY`, `OPENAI_API_KEY`).

The protocol described here regenerates **Table 2 (dose-response)**, **Table 3
(crossover at p=0.8)**, **Table 4 (cross-model)**, **Table 5 (authority bias)**,
and **Table 6 (Gamma decomposition)** of `main.tex`. Figure 1 (dose-response
curves), Figure 2 (reduction heatmap), and Figure 3 (ECE dose-response) are
re-rendered from the resulting JSONL by `figures/generate_figures.py`.

---

## 1. Experimental target and condition registry

The paper has two methodological layers that must both be reproduced. Face 1
is the **DeepSeek V4-Chat dose-response** layer. Two LLM agents (A and B)
perform 30 rounds of text summarization with peer memory context; one agent's
memory store is contaminated with a length-bias function at rate `p` and the
other agent retrieves from the contaminated memory. Face 2 is the
**cross-model / cross-bias** layer. The same three architectures are rerun on
Qwen3.7-Plus for length bias (10 rounds, 3 seeds) and for authority bias
(10 rounds, 3 seeds) at `p=0.8`. The joint protocol records the same
`Γ_temporal`, `Γ_content`, `Γ_retrieval`, and `ΔECE` metrics in both layers.

Use the eight condition identifiers below so every output row matches back to
`main.tex` Tables 2-6:

| condition_id | model            | bias type | architecture    | contamination `p` | seeds | rounds |
|---|---|---|---|---|---|---|
| D-A-02 | DeepSeek V4-Chat | length    | Append-Only     | 0.2 | 10 | 30 |
| D-A-05 | DeepSeek V4-Chat | length    | Append-Only     | 0.5 | 10 | 30 |
| D-A-08 | DeepSeek V4-Chat | length    | Append-Only     | 0.8 | 10 | 30 |
| D-S-02 | DeepSeek V4-Chat | length    | Summarization   | 0.2 | 10 | 30 |
| D-S-05 | DeepSeek V4-Chat | length    | Summarization   | 0.5 | 10 | 30 |
| D-S-08 | DeepSeek V4-Chat | length    | Summarization   | 0.8 | 10 | 30 |
| D-R-02 | DeepSeek V4-Chat | length    | RAG + Filter    | 0.2 | 10 | 30 |
| D-R-05 | DeepSeek V4-Chat | length    | RAG + Filter    | 0.5 | 10 | 30 |
| D-R-08 | DeepSeek V4-Chat | length    | RAG + Filter    | 0.8 | 10 | 30 |
| Q-A-08 | Qwen3.7-Plus     | length    | Append-Only     | 0.8 |  3 | 10 |
| Q-S-08 | Qwen3.7-Plus     | length    | Summarization   | 0.8 |  3 | 10 |
| Q-R-08 | Qwen3.7-Plus     | length    | RAG + Filter    | 0.8 |  3 | 10 |
| Q-A-AU | Qwen3.7-Plus     | authority | Append-Only     | 0.8 |  3 | 10 |
| Q-S-AU | Qwen3.7-Plus     | authority | Summarization   | 0.8 |  3 | 10 |
| Q-R-AU | Qwen3.7-Plus     | authority | RAG + Filter    | 0.8 |  3 | 10 |

That is `3 × 3 × 10 = 90` DeepSeek length experiments plus `3 × 2 × 3 = 18`
Qwen cross-validation experiments, for **108 paired (biased, clean) runs**
or **162 single-arm runs** counting both members of each pair (the number
quoted in the paper).

The RAG dense variant (SVD-64 on TF-IDF, `θ=0.3`) is **not part of the
canonical condition registry**; it is reported only in §3.5 of `main.tex` as
a sensitivity probe with five seeds at `p=0.5`. Reproducers may skip it.

---

## 2. Models, endpoints, snapshots, and rate limits

The paper names two families directly. The reproduction harness also
configures an external-judge slot for sensitivity. Pin the aliases below and
record the provider response model/version string for every call:

| family | model alias / snapshot | endpoint | role | conservative limit |
|---|---|---|---|---|
| DeepSeek   | `deepseek-v4-chat` (a.k.a. V4-Chat; if retired, use `deepseek-chat` and record the exact deployment name) | `https://api.deepseek.com/v1/chat/completions` | D-A-02..D-R-08 executor and summarizer | 30 requests/minute, retry after 429 |
| Qwen / DashScope | `qwen3.7-plus` | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | Q-A-08..Q-R-AU executor and summarizer | 30 requests/minute, retry after 429 |
| OpenAI / Azure OpenAI (optional) | `gpt-4o-2024-05-13` | `https://api.openai.com/v1/chat/completions` | external-judge slot for sensitivity | 30 requests/minute, 2 s cooldown |

Temperature settings: **temperature = 0.0** for all solver calls and
summarizer calls (the paper requires determinism, see §Reproducibility). Set
`max_tokens=512` for solver calls, `max_tokens=256` for summarizer calls, and
`max_tokens=64` for the external judge (if used). All provider keys must come
from environment variables; **never** persist them in JSONL outputs.

The DeepSeek V4-Chat snapshot at submission time resolved to the
`deepseek-v4-chat` model identifier on `https://api.deepseek.com`. Pin this
in `reproduce_peer/config.yaml`:

```yaml
models:
  deepseek:
    alias: deepseek-v4-chat
    endpoint: https://api.deepseek.com/v1/chat/completions
    temperature: 0.0
    max_tokens: 512
  qwen:
    alias: qwen3.7-plus
    endpoint: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
    temperature: 0.0
    max_tokens: 512
rate_limits:
  requests_per_minute: 30
  cooldown_seconds: 2
```

---

## 3. Multi-agent setup, communication topology, and memory architectures

Each condition uses **exactly two LLM agents** (`agent_A` and `agent_B`) that
communicate bidirectionally. The topology is a complete directed graph
without self-loops: after round `t`, each agent receives the previous-round
output of the other agent before solving round `t+1`. In the **clean**
reference arm both agents retrieve from an uncontaminated store; in the
**biased** arm, the same two agents are run again with one of the three
memory architectures and `p` fraction of stored outputs replaced by the
length-bias function (or by fabricated citations, for authority bias).

### 3.1 Architecture 1 — Append-Only

```text
M_t = {o_1, o_2, ..., o_t}
Retrieve(M_t, x) = last-K of {o_i}, ordered by recency, K = 5
```

Every output `o_i` is stored verbatim. Retrieval returns the most recent five
peer outputs in chronological order; this is the paper's "recency" baseline.
There is no summarization, no embedding, no filter.

### 3.2 Architecture 2 — Summarization (`k=1`)

After each round, the LLM summarizes its just-produced output:

```text
s_t = LLM-Summarize(o_t)
M_t = {s_1, s_2, ..., s_t}
Retrieve(M_t, x) = last-K summaries, K = 5
```

Use the **summarizer prompt in §4.4** below. The per-round consolidation
frequency `k=1` was selected in §3.5 of `main.tex` to maximize compression
and was confirmed in preliminary experiments with five seeds at `p=0.5`.

### 3.3 Architecture 3 — RAG with TF-IDF relevance filter

```text
e_i = TF-IDF(o_i)                # fit on the agent's own M_t
Retrieve(M_t, x) = {o_i : cosine(TF-IDF(x), e_i) > theta}
```

Set `theta = 0.1`. Biased memories whose TF-IDF cosine to the current query
falls below `0.1` are deprioritized. The TF-IDF vectorizer should use
`max_features=4096`, `ngram_range=(1, 2)`, `min_df=1`, `sublinear_tf=True`.
The **dense SVD-64 variant** uses `TruncatedSVD(n_components=64,
random_state=seed)` on the same TF-IDF features and `theta = 0.3`; this is a
sensitivity probe only and is not part of the canonical registry.

### 3.4 Bias injection

For **length bias**, every stored output that falls in the contaminated
fraction is replaced by:

```text
beta(o) = o ++ filler(alpha * len(o) - len(o))
```

with `alpha = 1.5` (50% expansion). `len(·)` counts whitespace-delimited
tokens. `filler(delta)` draws `delta` tokens uniformly without replacement
from the **filler pool** in §4.5. The contaminated fraction is selected
randomly **once per seed at the start of the run**, using
`reproduce_peer/seed_lock.py:seed_for(condition_id, seed_id, agent_id, "bias_mask")`.

For **authority bias**, the same mechanism applies but the replacement is
**prepending one fabricated citation** drawn uniformly from §4.6 to the
output text. Length is left unmodified.

---

## 4. Prompt templates (copy-paste exact text)

All prompts must be sent verbatim. Newlines, leading spaces, and the literal
braces are part of the contract.

### 4.1 Summarization task system prompt (both agents)

```text
You are agent {agent_id}, a careful and concise research summarizer.
You will read a short passage and write a 3-5 sentence summary.
You will also see recent outputs produced by your peer agent.
Use peer context to stay consistent in style and coverage, but
write the new summary independently. Do not copy phrases verbatim
from peer context unless they are exact technical terms.
```

### 4.2 Per-round user prompt (clean and biased arms)

```text
[PEER UPDATE -- ROUND {previous_round}]
Peer agent {peer_id} (round {previous_round}) wrote:
\"\"\"
{peer_output_or_memory_retrieval}
\"\"\"
Now summarize the new passage:

{passage_text}

Write exactly 3-5 sentences. End your reply with the literal token
[SUMMARY_END] on its own line.
```

For the clean arm `{peer_output_or_memory_retrieval}` is replaced by the
last-1 output of the peer agent (recency retrieval). For the biased arm it is
replaced by whatever the architecture returns: last-5 for Append-Only, last-5
summaries for Summarization, or the filtered top-K set for RAG.

### 4.3 Isolated baseline prompt (no peer context, optional sanity arm)

```text
Summarize the following passage in 3-5 sentences.
End your reply with the literal token [SUMMARY_END] on its own line.

{passage_text}
```

### 4.4 Summarizer call prompt (Architecture 2 only)

```text
You are a strict summarizer used for memory compression. Reduce the
following agent output to a single sentence that preserves factual
content, named entities, and any length or authority markers. Do not
add new information. Do not change named entities. Do not paraphrase
into hedged language.

Input output:
\"\"\"
{agent_output}
\"\"\"

Compressed sentence:
```

### 4.5 Length-bias filler pool

The filler pool is sampled uniformly without replacement. Tokens are joined
by single spaces and prepended to the contaminated output:

```text
arguably  ,  broadly  ,  conceivably  ,  in essence  ,  in general  ,
interestingly  ,  it could be argued that  ,  it seems plausible that  ,
on the whole  ,  overall  ,  perhaps  ,  plausibly  ,  presumably  ,
put differently  ,  that is to say  ,  to some extent  ,  typically  ,
unlike cases where  ,  whereas  ,  while in some sense
```

Each entry is one token in the token count; the comma is part of the
artificial pool syntax and is not sent to the model.

### 4.6 Authority-bias citation pool (Qwen3.7-Plus authority arm only)

```text
[Smith et al., 2024, ACL]
[Johnson and Lee, 2023, NeurIPS]
[Patel et al., 2025, TMLR]
[Brown and Davis, 2022, ICML]
[Garcia et al., 2024, JMLR]
[Chen and Wang, 2023, EMNLP]
[Anderson et al., 2025, ICLR]
[Liu and Zhang, 2024, NAACL]
```

One citation is prepended to the contaminated output verbatim.

### 4.7 Passage corpus

The protocol uses a **fixed 30-passage English text-summarization corpus**
sampled from CNN/DailyMail test split, restricted to passages between 250
and 400 whitespace-delimited tokens. The seed-controlled sample is
generated by `reproduce_peer/load_corpus.py`:

```python
from datasets import load_dataset
ds = load_dataset("cnn_dailymail", "3.0.0", split="test")
rng = np.random.default_rng(20260708)
idx = rng.choice(len(ds), size=30, replace=False)
passages = [ds[int(i)]["article"][:5000] for i in idx]
```

Passages are stored as `data/passages.jsonl` with `{"passage_id", "text"}`.
Every experiment uses the **same ordered 30-passage list** regardless of
seed or architecture.

---

## 5. Evaluation methodology

### 5.1 Γ_temporal (primary metric)

`Γ_temporal` is the Wasserstein-1 distance between normalized output-length
distributions of the **biased** and **clean** arms of a paired condition:

```text
Gamma_temporal = W1(P_biased_hat, P_clean_hat)
```

`P_*_hat` is the empirical distribution of normalized output lengths.
Output length is z-scored within each arm of each paired condition (z =
`(len(o) - mean(len_clean)) / std(len_clean)`). For the Decomposition Table 6,
z-scoring uses the union of biased + clean lengths. W_1 is computed with
`scipy.stats.wasserstein_distance` over `n_rounds = 30` (or 10 for Qwen)
samples per arm.

### 5.2 Γ decomposition

```text
Gamma_temporal = Gamma_content + Gamma_retrieval
```

`Γ_content` measures the difference between stored-content distributions
and equals `Γ_temporal` for Append-Only and RAG (which store outputs
verbatim). For Summarization, `Γ_content` is the W_1 distance between
summarized lengths in the biased vs clean arm. `Γ_retrieval` is the residual
`Γ_temporal - Γ_content`; for Append-Only and RAG it is zero, and for
Summarization it captures the effect of compression on the retrieval index.

### 5.3 ΔECE (calibration degradation)

Calibration error is computed in 10 equal-width bins over `[0, 1]`:

```text
ECE = sum over bins b of (|B_b| / n) * |mean_confidence(B_b) - mean_accuracy(B_b)|
```

Confidence is parsed from the line `Confidence: <float>` in the model output.
If the line is missing, set `confidence = NaN` and drop the sample from ECE
computation. Correctness is judged by **Rouge-L F1 ≥ 0.30** against the
reference summary; a stricter C13-style external judge can be substituted.

`Delta_ECE(condition) = ECE_final(condition) - ECE_final(clean baseline at matched architecture)`
where the clean baseline is the no-contamination arm of the same architecture
at the same model, seed, and horizon. The paper-level reference values are:
`ΔECE(Summarization, p=0.8) ≈ -0.03`, `ΔECE(RAG, p=0.8) ≈ +0.01`,
`ΔECE(Append-Only, p=0.8) ≈ +0.04`.

### 5.4 Statistical methods

- **Two-sample t-test** for each pairwise comparison; report raw `t`,
  `p_raw`, `p_adj`, and **Cohen's `d`** in parentheses.
- **Bootstrap 95% CI**: 1000 resamples of the per-seed `Γ_temporal` values.
- **Holm-Bonferroni correction** across the 9 pairwise comparisons
  (3 architectures × 3 contamination rates for DeepSeek length). For the
  Qwen cross-validation table, apply Holm across the 3 architecture
  comparisons.
- **Power**: with `n = 10` seeds, the DeepSeek study has ~80% power for
  large effects (`d > 0.8`); for the Qwen arm (`n = 3` seeds) report
  `mean ± range` and do **not** perform pairwise t-tests.

---

## 6. 6,000-call budget and runtime

A reproducible call is one solver-model API completion or one summarizer
call. Evaluator calls and TF-IDF fits are offline. The total budget is:

| layer | conditions | calls = seeds × architectures × contamination × rounds × 2 agents |
|---|---:|---:|
| DeepSeek length (Face 1)   | 9 (3 × 3 contamination) | 10 × 3 × 3 × 30 × 2 = **5,400** |
| Qwen length (Face 2)       | 3                       |  3 × 3 × 1 × 10 × 2 = **180**    |
| Qwen authority (Face 2)    | 3                       |  3 × 3 × 1 × 10 × 2 = **180**    |
| External judge (optional)  | —                       | **600** (5% sample of Face 1)    |
| **Total**                  | 15 conditions, 162 single-arm runs | **6,360 calls** (5,760 without judge) |

The paper headline number is **"approximately 5,400 LLM calls"** for the
DeepSeek Face 1 alone; the **162 total experiments** figure in the abstract
counts both members of each biased/clean pair. The reproduction runner
should emit one JSONL per condition and one combined `outputs/protocol_run.jsonl`.

**Expected cost**: at the time of writing, DeepSeek V4-Chat charges
approximately $0.14 per 1M input tokens and $0.28 per 1M output tokens; with
~300 input tokens and ~250 output tokens per call, the DeepSeek Face 1 alone
costs approximately **$1.20–1.50**. Qwen3.7-Plus is similarly priced. The
full 6,360-call reproduction therefore costs approximately **$2–4**.

**Expected wall-clock**: with 30 requests/minute rate limits and three
asynchronous workers, Face 1 takes 60–90 minutes. Adding Face 2 and
buffered retries, the full protocol runs in **2–4 hours**. Sequential
single-worker runs require **6–8 hours**.

---

## 7. Random seed handling (`reproduce_peer/seed_lock.py`)

All random choices — corpus sampling indices, contamination masks, tie
breaking, TF-IDF random state, SVD random state, bootstrap resamples — must
flow through `reproduce_peer/seed_lock.py`. The file should define a
deterministic function equivalent to:

```python
def seed_for(
    condition_id: str,
    seed_id: int,
    agent_id: str,
    purpose: str,
    base_seed: int = 20260708,
) -> int:
    """
    Derive a deterministic 32-bit seed for any random choice.

    Args:
        condition_id: e.g. "D-A-02", "Q-S-AU"
        seed_id:      integer seed index, 0..9 (DeepSeek) or 0..2 (Qwen)
        agent_id:     "agent_A" or "agent_B"
        purpose:      short tag for the use site:
                      "bias_mask"   - which outputs to contaminate
                      "corpus"      - corpus sampling offset (always 20260708)
                      "tfidf"       - TF-IDF vectorizer seed (unused, deterministic)
                      "svd"         - TruncatedSVD random_state
                      "bootstrap"   - bootstrap resample index
        base_seed:    master salt (date stamp of paper version)
    Returns:
        Unsigned 32-bit integer suitable for np.random.default_rng.
    """
    import hashlib
    key = f"{base_seed}:{condition_id}:{seed_id}:{agent_id}:{purpose}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest()[:16], 16) % (2**32)
```

Use this seed to:

- select the contamination mask (binary array of length `n_rounds`);
- seed the TF-IDF `sublinear_tf` tie breaker;
- seed `TruncatedSVD(random_state=...)` for the dense variant;
- seed `np.random.default_rng(...)` for bootstrap resamples.

API models are not perfectly deterministic even at temperature 0, so
**reproducibility requires storing**: raw prompts, raw responses, provider
request IDs, model aliases, timestamps, retry counts, and the seed used for
every random choice. Seeds are matched across architectures:
`seed_id=7` must see the same contamination mask and the same ordered
passage list in every architecture of the same condition. The corpus sampling
offset (`purpose="corpus"`) is fixed at `base_seed` and independent of
`seed_id`.

---

## 8. Output format

Write one JSON object per API completion to `outputs/protocol_run.jsonl`.
**Required** fields are exactly:

```json
{
  "condition_id": "D-S-08",
  "agent_id": "agent_A",
  "prompt": "...full prompt sent to provider...",
  "response": "...raw model response...",
  "calibration_score": 0.72,
  "timestamp": "2026-07-08T00:00:00Z"
}
```

**Recommended additional fields**:

| field | type | meaning |
|---|---|---|
| `seed_id` | int | 0..9 for DeepSeek, 0..2 for Qwen |
| `round` | int | 0-indexed round number (0..29 or 0..9) |
| `model_family` | string | `"deepseek"` or `"qwen"` |
| `model_snapshot` | string | provider response model id |
| `endpoint` | string | full URL used |
| `architecture` | string | `"append"`, `"summarize"`, `"rag_tfidf"` |
| `contamination_rate` | float | `0.2` / `0.5` / `0.8` |
| `bias_type` | string | `"length"` or `"authority"` |
| `bias_applied` | bool | whether this round's stored output was contaminated |
| `memory_retrieval` | string | text actually returned by `Retrieve(M_t, x)` |
| `gamma_temporal` | float | recomputed Γ for this condition up to this round |
| `gamma_content` | float | recomputed Γ_content for this condition |
| `gamma_retrieval` | float | recomputed Γ_retrieval for this condition |
| `ece` | float | running ECE estimate (NaN if confidence missing) |
| `retry_count` | int | number of provider retries before success |
| `provider_request_id` | string | provider's request-id header |
| `output_length_tokens` | int | `len(response.split())` |
| `output_length_z` | float | z-scored length within this arm |

After completion, run:

```bash
python scoring/gamma_monitor.py \
    --input outputs/protocol_run.jsonl \
    --output reports/gamma_summary.json
```

to emit per-condition final `Γ_temporal`, `Γ_content`, `Γ_retrieval`,
`ΔECE`, and bootstrap CIs. Then run:

```bash
python figures/generate_figures.py --input reports/gamma_summary.json
```

to regenerate `figures/dose_response_curves.pdf`,
`figures/reduction_heatmap.pdf`, and `figures/ece_dose_response.pdf`. Compare
the resulting numbers against Tables 2-6 of `main.tex`. **Do not average
across architectures** when reporting dose-response; report every cell of
Tables 2 and 6, not just the marginal means.

---

## 9. What to check against the paper

Once `gamma_monitor.py` finishes, the reproducer should be able to fill in:

- **Table 2** (DeepSeek length dose-response, 9 cells, mean ± std, 95% CI in brackets). Expected ranges from `main.tex`:
  - D-A-02: 0.42 ± 0.14 [0.24, 0.63]
  - D-A-05: 0.39 ± 0.09 [0.25, 0.52]
  - D-A-08: 0.27 ± 0.06 [0.19, 0.33]
  - D-S-02: 0.41 ± 0.12 [0.20, 0.57]
  - D-S-05: 0.32 ± 0.10 [0.19, 0.49]
  - D-S-08: 0.19 ± 0.07 [0.12, 0.32]
  - D-R-02: 0.30 ± 0.10 [0.13, 0.44]
  - D-R-05: 0.32 ± 0.09 [0.18, 0.43]
  - D-R-08: 0.25 ± 0.05 [0.20, 0.34]
- **Table 3** (DeepSeek pairwise at p=0.8): Summarization vs Append-Only
  `t=2.70, p_adj=0.045, d=1.21`; RAG vs Append-Only `t=0.90, p_adj=0.381, d=0.40`;
  Summarization vs RAG `t=-2.07, p_adj=0.106, d=0.93`.
- **Table 4** (Qwen cross-model at p=0.8, length): Q-A-08 = 0.43,
  Q-S-08 = 0.58 (+35%), Q-R-08 = 0.54 (+25%). **Sign reversal vs DeepSeek is
  the key finding.**
- **Table 5** (Qwen authority at p=0.8): Q-A-AU = 0.39, Q-S-AU = 0.81 (+107%),
  Q-R-AU = 0.57 (+46%). **Both architectures amplify on authority bias.**
- **Table 6** (Decomposition): for Append-Only and RAG, retrieval column is
  0.000 across all contamination rates; for Summarization the retrieval
  component is 0.225 at p=0.2 and 0.015 at p=0.8.

A reproduction is **acceptable** if every reported cell falls within the
paper's 95% bootstrap CI (or within ±0.05 for the Qwen cross-validation
where `n=3` seeds precludes tight CIs). Any cell whose point estimate falls
**outside** the paper's CI by more than 0.05 should be flagged in
`reports/reproduction_report.md` and investigated before publication.

---

## 10. Practical reproduction checklist

1. `git clone https://anonymous.4open.science/r/memory-architecture-bias-F720/`
2. `pip install -r requirements.txt`  (numpy, scipy, scikit-learn, requests, datasets, matplotlib)
3. `export DEEPSEEK_API_KEY=...`  and `export QWEN_API_KEY=...`
4. `python reproduce_peer/load_corpus.py` → `data/passages.jsonl`
5. `python reproduce_peer/run_protocol.py --config reproduce_peer/config.yaml`
6. `python scoring/gamma_monitor.py --input outputs/protocol_run.jsonl`
7. `python figures/generate_figures.py --input reports/gamma_summary.json`
8. Compare `reports/gamma_summary.json` to Tables 2-6 of `main.tex`.
9. If any cell fails the §9 acceptance check, file an issue at the
   GitHub repository with the failing condition_id, seed_id, and the
   provider request_id of the offending call.

License: MIT. Data sources: CNN/DailyMail test split (`cnn_dailymail` 3.0.0)
under Apache-2.0; DeepSeek and Qwen APIs under their respective provider
terms. No PII is collected; all prompts and responses are model-generated
text on public-domain passages.