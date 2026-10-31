# Proudmoore scanner: first milestone

Implement the first milestone of the implementation plan agreed in chat on 2026-10-31.

- Collect live Retail Proudmoore-US item, US commodity, and US regional item CSV files from TSM's documented public feeds.
- Validate schemas, prices in copper, identifiers, timestamps, demand-field coverage, and missing/zero demand. Preserve separate market scopes.
- Persist deduplicated source scan metadata and a bounded history of at most 100 shortlisted item observations per scan, retained for 35 days. Do not pretend to retain full auction history.
- Produce a machine-readable report, Markdown validation report, and mobile-readable self-contained HTML watchlist.
- Apply a 20% minimum return on purchase cost after a configurable AH cut, resale markdown, and lost-deposit allowance. A 4,000g unit cap, 4,000g item exposure, 40,000g capital, and 10,000g reserve are planning limits.
- Use regional sale estimates as demand evidence, never as confirmed Proudmoore sales or personal sell-through probabilities.
- All results are research-only: no actionable buys or quantity recommendations until exact item identity, current listings, inventory, and sufficient history have been verified. No automatic trades.
- A stale or invalid feed must be visible. Unknown schemas and corrupted state must fail safely. A failed run must replace any report with an unavailable report rather than retain actionable results.
- Provide an explicitly labelled synthetic demo and automated checks of financial and ingestion boundaries.
- Run hourly in GitHub Actions, restore durable state from a dedicated branch, publish report artifacts, and support manual runs. Never place tokens, credentials, or personal transactions in reports. The user explicitly selected public repository visibility on 2026-10-31 after private runners were blocked by account billing.

Deferred: Blizzard OAuth and live auction depth, token price integration, verified item whitelist, Journalator import and cost-basis accounting, private hosted dashboard, actionable recommendations, daily aggregates, and profitability evaluation after a real trading trial.
