# Proudmoore Market Watch

A research-only WoW Retail market scanner for Proudmoore-US. Runs without a gaming PC or active WoW subscription. Python 3.11+; no third-party Python dependencies.

[Repository](https://github.com/rclee/proudmoore-market-scanner) · [Hourly runs and report downloads](https://github.com/rclee/proudmoore-market-scanner/actions/workflows/scan.yml) · [Initial data findings](docs/DATA_VALIDATION.md)

**Daily phone page:** [Proudmoore Daily Gold](https://proudmoore-daily-gold.airofcozy.chatgpt.site) (owner-private; sign in with the owner's ChatGPT account). It shows a skip-first decision, a local vendor-profit checker, TSM shopping setup, and up to three optional commodity research leads. No verified vendor deals are currently supplied by the public feeds, which lack vendor sell values.

The enriched version adds live-build vendor references covering most US commodities, newer AHledger commodity quantities and seven-day snapshot history, a timestamped US token price, public r/woweconomy and TSM blog feeds, and a daily procedural brief. References and snapshots remain conditional; the brief does not turn them into verified game quotes. See [data-source research](docs/MORE_DATA_RESEARCH.md), [community access](docs/COMMUNITY_SOURCES.md), and the [trading playbook](docs/TRADING_PLAYBOOK.md).

**This first milestone produces a watchlist, not actionable purchase recommendations.** It cannot prove that an auction sells, verify current listing depth or equipment variants, read your inventory, or guarantee subscription funding.

## Run locally

From this project folder:

```powershell
python -m scanner
python -m scanner.enrich
python -m scanner --demo
python -m unittest discover -s tests -v
```

Live output: `output/live/index.html`, `report.json`, and `validation.md`. Open the HTML file in a browser; it is self-contained and works offline. Demo output is isolated in `output/demo/` and uses explicitly synthetic records. Demo never reads or writes live state.

## What it collects

The documented [TSM public CSV feeds](https://tradeskillmaster.com/public-data):

- Proudmoore base item pricing: `https://public-data.tradeskillmaster.com/retail/us/realm/proudmoore/items.csv`
- US commodity pricing: `https://public-data.tradeskillmaster.com/retail/us/commodities.csv`
- US regional item and demand estimates: `https://public-data.tradeskillmaster.com/retail/us/region/items.csv`

These are separate market scopes. Market files refresh every few hours; region files daily. The scanner uses upstream `updatedAt`, not fetch time, for freshness. No TSM key is needed. Demand estimates do not establish actual Proudmoore sales or your personal chance of a sale.

`scanner.enrich` follows a successful core scan. Wago's homepage identifies the live Retail product `wow`; the collector pins that build and reads ItemSparse. Non-equipment stackable records with no inspected level curves provide reference sell prices. The catalog is cached for 24 hours in durable SQLite and the live-build lookup for four hours; the full CSV is never published. A bounded set of at most 15 AHledger US commodity history reads (plus vendor corroboration where still relevant), one token feed, and two community feeds run independently. Network outages stop a provider, and an overall enrichment budget leaves time for core report publication. All external data keeps its source and timestamp.

Public r/woweconomy RSS access was verified. Reddit JSON was blocked; r/wowgoblins RSS was rate-limited, so neither is bypassed. Community headline collection is not equivalent to automated expert reading of every discussion. Older TSM blog entries retain their original dates.

Schemas, positive demand coverage, row counts, timestamps, filters, and history coverage appear in each validation report. The scanner strictly rejects malformed rows, duplicate IDs, negative/fractional copper, future/mixed scan timestamps, and missing required columns. New extra columns are tolerated. Changed content under an existing source scan timestamp fails safely for inspection.

## Research pricing

`config.json` sets all planning assumptions. The default 20% threshold means **net return on purchase cost**, not margin on revenue.

1. Take the minimum positive value of local market value, local historical price, local recent price, and regional average sale price.
2. Apply a 10% resale markdown.
3. Subtract a configurable 5% AH cut and 1g lost-deposit allowance per unit.
4. Divide the resulting proceeds by 1.20 to obtain a research buy ceiling, capped at 4,000g.

Require regional sale rate >= 0.10 and sold per day >= 1. These are provisional research filters, not guarantees. All calculations use integer copper and round conservatively. All recommended quantities remain **zero**; inventory, aggregate budget, exposure, and exact live auctions must be verified before a future recommendation engine can allocate capital. The displayed 40,000g budget and 10,000g reserve are planning values, not a fetched wallet balance.

## Cloud operation

`.github/workflows/scan.yml` runs checks and scans on pushes to main, manual dispatch, and hourly at minute 47 UTC. It restores history from a dedicated `scanner-state` branch, deduplicates source scan timestamps, and pushes updated history without modifying source commits. Pull requests run checks only. The branch stores a compact SQLite database; report artifacts are retained for 14 days.

Each scan preserves at most 100 shortlisted observations; rows expire after 35 days. This is **not full market history**. State failure stops collection rather than silently starting over. A failed download writes an unavailable report and exits nonzero. Stale data is labelled and also causes a failed run. The HTML checks source expiration while open, including when it is an older downloaded artifact.

The repository is public, as requested by its owner to use standard public-repository runners after an account billing restriction blocked private runs. Include only public market data; never add personal transactions or credentials. In GitHub, open **Actions → Market scan → latest successful run** to read the validation summary and download its full report artifact (GitHub sign-in may be required). The separate `scanner-report` branch publishes only the generated report JSON and HTML; the phone page fetches its public JSON every five minutes while open. Failed collection reports also replace that public feed. Durable history remains on `scanner-state`.

GitHub schedules can be late or skipped, and public schedules may be disabled after 60 days without repository activity. The dashboard must not be treated as a live quote. [GitHub schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

## Next milestones

1. Collect 7–14 days and inspect candidate persistence; do not simulate completed sales from disappearing listings.
2. Add Blizzard OAuth credentials in GitHub Secrets; resolve Proudmoore's connected realm and inspect exact auctions, quantities, quality, and modifiers. No Blizzard credentials are required for this milestone.
3. Add a verified whitelist, private inventory ledger, and allocation across capital/reserve/item exposure limits; then consider actionable candidates.
4. Add the current US token price with timestamp. Owner-private phone hosting is live; calculator inputs stay local to the page. Public report data contains no personal transactions or credentials.
5. Install addons after choosing to subscribe; import a real Journalator CSV sample, deduplicate records, reconcile fees and cost basis, and track realized profit separately from unsold inventory.
6. Run a two-week manual trading trial with a proposed 4,000g loss limit and 15-minute session limit. Reassess the target using the actual token price.

At 20% return on cost, 300,000g monthly profit needs about 1,500,000g in completed purchase/resale turnover. A 40,000g starting budget may not sustain that. This tool exists to test feasibility before risking the rest of your gold.
