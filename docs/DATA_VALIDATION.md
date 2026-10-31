# Initial live-data validation

Collected 31 October 2026 at 16:06 UTC (17:06 Europe/Berlin). These counts describe one snapshot, not ongoing performance.

| Feed | Rows | Upstream scan, UTC | Unnamed records |
| --- | ---: | --- | ---: |
| Proudmoore-US non-commodity items | 17,262 | 31 Oct 11:32 | 102 |
| US commodities | 10,977 | 31 Oct 14:33 | 170 |
| US regional item estimates | 29,995 | 30 Oct 08:44 | 283 |

Source: [TradeSkillMaster public pricing data](https://tradeskillmaster.com/public-data). The three documented CSV endpoints were successfully downloaded and parsed; no subscription or TSM API key was required.

## Confirmed format

- Market files: `itemId,name,marketValue,minBuyout,recent,historical,updatedAt`.
- Region file: `itemId,name,marketValue,historical,avgSalePrice,saleRate,soldPerDay,updatedAt`.
- Prices are integer copper; source timestamps were UTC and uniform within each file.
- There were 21,202 regional rows with both positive sale rate and positive sold-per-day estimates.
- Some rows have empty item names. The collector counts these records; the watchlist excludes them.

## Initial filter result

18 research candidates passed the configured price and demand filters: 13 realm items and 5 commodities. All recommended quantities were zero. This does not establish low purchase risk, available quantities, actual sell-through, or profitability.

The oldest input was the regional daily file, about 31 hours old. The initial tolerances are 6 hours for market data and 48 hours for region data. These are explicit freshness thresholds, not a claim that prices remain executable that long.

## What remains unverified

- Exact current listings, auction depth, and item variants: need Blizzard auction API integration and in-game checks.
- Demand on Proudmoore: regional estimates cannot prove realm-level sales.
- Persistence of discounts: requires repeated snapshots over 7–14 days.
- Realized net profit, costs, and time spent: requires the manual trading trial and Journalator reconciliation.
- Token affordability: no current token feed is connected.

The gaming PC can stay off while the cloud collects future observations. The user subsequently selected a public repository; reports contain public market observations and no personal transactions.
