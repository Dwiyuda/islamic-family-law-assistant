# Generation evaluation

| Group | n | answered | fallback | in_domain_refused | out_of_domain_refused | out_of_domain_below_threshold | citation_precision | steps_kept | faithfulness | answer_relevancy | n_scored | n_nan | n_error | inheritance_numbers_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ask/gold | 100 | 78 | 0 | 0.025 | 1.000 | 0.950 | 1.000 | — | 0.827 | 0.731 | 69 | 0 | 0 | 0.414 |
| ask/heldout | 40 | 20 | 0 | 0.000 | 1.000 | 0.650 | 1.000 | — | — | — | 0 | 0 | 0 | 0.000 |
| navigator/gold | 35 | 34 | 0 | 0.029 | — | — | 1.000 | 55/55 | — | — | 0 | 0 | 0 | — |

Targets (spec 8.2): faithfulness ≥ 0.85; out-of-domain refused ≥ 90%; in-domain wrongly refused ≤ 10%.

- `gold` rows reuse the threshold fitted on the same 100 gold questions (in-sample); `heldout` rows are out-of-sample (eval/heldout.jsonl, never used for fitting).
- Faithfulness and answer relevancy are LLM-judged (RAGAS prompts are English, answers Indonesian); treat small differences as noise. If the judge model equals the generator, the judge grades its own model family.
- `out_of_domain_below_threshold`: refused by the retrieval threshold alone, before the LLM.
- `n_nan`: scored rows whose RAGAS metric is NaN (no statements extracted); `n_error`: rows the judge failed on for a non-transient reason. Both are left out of the means.
- inheritance_numbers_rate: share of answered kewarisan Q&A answers that state shares/fractions; spec 2.3 says amounts come from the faraid engine (Fase 4), so this is tracked as a known risk.

## Run configuration

- provider: `gemini`, model: `gemini-flash-lite-latest`, judge model: `gemini-flash-lite-latest`
- prompt version: `9414822348b2`, REFUSAL_THRESHOLD: 0.0333
- ragas: 0.4.3, date: 2026-10-18
