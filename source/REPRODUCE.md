# PAPER5 Round-3 Reproduction README

Status: Round-3 collection and offline confirmatory analysis completed on 2026-07-14.

This README documents how to verify the Round-3 evidence package used by `main.tex`. It supersedes the earlier cached-log and mock-mode notes for the confirmatory results.

## Files to Archive With the Manuscript

The Round-3 evidence package lives in the Haolo output directory and should be copied or archived with the paper submission package:

- `paper5_round3_validator_report_final_20260714.json`
- `paper5_round3_final_collection_validation_20260714.json`
- `paper5_round3_confirmatory_results_20260714.csv`
- `paper5_round3_confirmatory_analysis_manifest_20260714.json`
- `paper5_round3_empty_response_quarantine_manifest_20260714.json`
- `paper5_round3_deviation_record_20260714.md`

## Verification Checklist

1. Confirm the final validator report has `accepted: true`.
2. Confirm the final collection validation reports `row_count_and_schema_passes: true`.
3. Confirm the final raw collection has `120` seed-condition JSONL files and `2,400` solver-completion rows.
4. Confirm no `.partial` files remain.
5. Confirm no primary solver row has empty response text or blank request id.
6. Regenerate the confirmatory analysis from the final raw JSONL, not from intermediate summaries.
7. Compare the regenerated CSV to `paper5_round3_confirmatory_results_20260714.csv`.

## Confirmatory Result to Match

No architecture contrast survives within-model Holm correction at `.05`.

The strongest directional contrast is Qwen3.7-Plus authority bias, Summarization minus Append-Only:

- mean paired difference: `-0.2579`
- 95 percent bootstrap CI: `[-0.4348, -0.0787]`
- raw p-value: `0.0255`
- Holm-adjusted p-value: `0.1020`
- paired effect size `d_z`: `-0.8452`

## Recovery and Deviation Notes

The collection was not a single uninterrupted execution trace. Provider timeouts interrupted the final Qwen RAG+Filter authority block, and recovery reran only missing or partial seed-condition files. A later offline audit found 17 empty primary responses in 13 earlier DeepSeek files; those files were quarantined with hashes and regenerated after the runner was changed to retry empty primary solver outputs.

The final logs therefore contain mixed configuration and runner hashes. This is reported as a provenance limitation in the manuscript, while the final row count, schema validation, and offline recomputation pass.