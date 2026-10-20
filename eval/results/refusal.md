# Refusal threshold

Refuse when the top reranker score is below **0.0333**.

| Metric | Value | Target (spec 8.2) |
|---|---|---|
| Out-of-domain refused | 95.0% | ≥ 90% |
| In-domain wrongly refused | 1.2% | ≤ 10% |

These figures are in-sample: the threshold was fitted on the same 80 in-domain + 20 out-of-domain questions it is scored against, and 20 out-of-domain questions is a small sample, so treat the percentages as optimistic.

## Margin

- Highest refused out-of-domain score: 0.0136 (luar-016)
- Lowest non-refused in-domain score: 0.0530 (waris-022)
- Misclassified: luar-002 not refused (0.1304); cerai-031 wrongly refused (0.0088)
