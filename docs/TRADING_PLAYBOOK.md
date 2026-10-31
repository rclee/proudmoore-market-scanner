# Proudmoore trading playbook

The user's daily job is to read a short brief, execute bounded manual actions, and log off within 15 minutes. Research belongs in the tool and this repository, not in the user's daily routine.

## Market and capital

- Retail, Proudmoore-US for non-commodities. Commodity orders are US-wide.
- Original trading allocation: 40,000g with 10,000g held back. The daily vendor-check brief currently uses a smaller 1,000g combined session ceiling, up to three lots, at most 200 units per lot. Wallet/inventory remain unknown; ceilings are not actual holdings.
- No game automation or account access. Never issue a trade instruction from a social post alone.

## Evidence order

1. Exact in-game vendor payout and the final full-quantity purchase quote control execution.
2. Correct-market auction snapshots corroborate whether an old discount still exists. Total listed quantity is not depth at the cheapest price.
3. Pinned live Retail client data supports static vendor screening. Exclude equipment/scaling and corroborate eligible values independently before producing a conditional lot.
4. TSM history and regional sale estimates support research. They do not demonstrate personal/realm sales.
5. Reddit posts, TSM guides, and other community sources generate hypotheses. Publication date and game version matter; reported profits are not replicated results.

## Supported daily brief

The enabled strategy is direct vendoring of a purchased commodity, conditional on live confirmation. Require a matching independent vendor reference, a fresh newer commodity snapshot below 80% of the reference, at least 10g profit at the permitted total, and all session/lot limits.

Each conditional card supplies item identity, quantity to request, maximum whole-lot cost, required NPC payout, and snapshot time. If the current quote or exact payout differs, skip it. An unavailable/expired data check must replace buying instructions with skip instructions. Never infer completed transactions from vanished listings.

When nothing qualifies, the entire brief is: collect the user's own completed-sales mail; make no new purchases; log off. Do not fill the schedule with weak trades.

## Community hypotheses under consideration

See COMMUNITY_SOURCES.md for dated primary discussion links and access tests.

- Concentration crafting in small batches: potentially less daily work, but requires known professions, recipe/quality unlocks, reagent costs, and tested margins. The discussed earnings include hypothetical figures. Not enabled for this Hunter without those facts.
- Commodity resale: requires an executable purchase quote, conservative exit price, fees/deposit treatment, inventory tracking, and observed personal sell-through. Not enabled merely because a regional mean exceeds a minimum listing.
- Market resets, speculative hoarding, transmog, and cross-realm schemes: poor fit for the stated starting capital/time constraint without additional evidence. Exclude from the daily brief by default.

## Learning loop

The hourly cloud run collects community headlines and market evidence, screens all matched commodity vendor references, and emits bounded conditional checks. It does not autonomously understand every Reddit comment or establish live profitability. Future strategy promotion must record the originating source, falsifiable price/volume hypothesis, validation results, realized costs, and actual time required. Journalator reconciliation is needed for outcome-based calibration.

Current evidence does not establish sustained token funding. A broader Proudmoore realm-auction integration still needs Blizzard developer credentials or a provider with a verified Proudmoore-specific feed; never substitute Tichondrius.
