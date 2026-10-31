# Enrichment and daily brief review

Baseline scanner revision: efd8e127c8b5b06f270ef69caf4533ce9e55d2a5. Site baseline: 89c6a84b0452632a33870d4e26e211e9d6b72400.

## Standards

Three failure-path findings were corrected: malformed/null provider timestamps now become FeedError; null brief tasks are rejected before use; provider timeouts/outages stop remaining item requests and the enrichment stage has an overall deadline. Re-review found no remaining actionable Standards issue.

## Spec

Two findings were corrected: provider stalls could consume the entire workflow; stale task filtering could leave buying instructions visible after cards expired. Provider budgets now preserve publication time, and rejected/expired task sets receive skip instructions. Re-review found no remaining actionable Spec issue.

## Verification

- 28 Python behavioral tests and a clean type check.
- 11 JavaScript tests including stale instructions and malformed tasks.
- Actual live enrichment joined 10,890 of 10,977 commodity IDs against pinned Retail build12.1.5.70688. It fetched 15 newer US commodity snapshots with seven-day history and a US token price.
- All ten old-feed below-reference discounts were rejected by newer snapshot prices. No trade was represented as verified or executed.
- r/woweconomy Atom RSS and official TSM blog RSS worked. Reddit JSON403 and r/wowgoblins RSS429 were not bypassed.

Static vendor values can miss server hotfixes/context. Total supply is not cheapest-price depth. Community posts are research leads, and published profit claims remain unverified for this character. The playbook documents prerequisites before other strategies can enter the daily instructions.
