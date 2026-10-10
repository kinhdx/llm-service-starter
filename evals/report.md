# Triage evaluation: claude-haiku-5-5

Prompt version: 2026-10-10.1

| Metric | Value |
|---|---|
| cases | 40 |
| category_accuracy | 0.95 |
| urgency_accuracy | 0.775 |
| fraud_recall | 1 |
| human_route_recall | 1 |
| max_cost_per_case_usd | 0.00025 |
| total_cost_usd | 0.0059 |

Gate: passed

| Case | Category (expected) | Urgency (expected) |
|---|---|---|
| c10 | transfer (transfer) | high (normal) |
| c15 | transfer (transfer) | high (normal) |
| c18 | loan (loan) | normal (low) |
| c19 | fee (fee) | normal (low) |
| c22 | card (card) | high (normal) |
| c23 | fraud (card) | high (normal) |
| c26 | other (other) | normal (low) |
| c31 | fee (fee) | normal (low) |
| c33 | transfer (transfer) | high (normal) |
| c34 | fraud (account) | high (high) |
