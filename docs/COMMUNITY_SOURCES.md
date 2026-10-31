# Community intelligence sources — verified 31 October 2026

## Access that actually worked

| Source | Verified access | Freshness / scope | Suitable use |
| --- | --- | --- | --- |
| [r/woweconomy new posts RSS](https://www.reddit.com/r/woweconomy/new/.rss) | HTTP 200, Atom XML | Feed updated 31 Oct 2026 16:47:47 UTC; newest post 31 Oct | Discover current community hypotheses and discussions; not price quotes |
| [r/wowgoblins new posts RSS](https://www.reddit.com/r/wowgoblins/new/.rss) | HTTP 429 during this check | Not verified as available | Mark unavailable; honor Retry-After/backoff; do not invent coverage |
| [r/woweconomy JSON](https://www.reddit.com/r/woweconomy/new.json?limit=5) | HTTP 403 Blocked | Not usable here | Do not bypass the restriction or depend on it |
| [Official TSM blog RSS](https://blog.tradeskillmaster.com/feed/) | HTTP 200, RSS XML | Latest returned entry was 17 Nov **2024**, despite current access | Tool concepts/release announcements, not current market signals |
| [TSM support](https://support.tradeskillmaster.com/) | Public documentation available | Individual pages carry update dates | Validate custom strings, operations, caveats |
| [Saddlebag shortage-method guide](https://saddlebagexchange.com/blog/r3) | HTTP 200 HTML | Methodological guide; item examples are older expansion content | Hypothesis design, quantity/sales distinctions |
| [Saddlebag OpenAPI](https://docs.saddlebagexchange.com/openapi.json) | HTTP 200 JSON | Schemas include WoW commodity/futures/listing paths | Discover supported requests; access to data endpoints not established by an open schema |
| [Journalator source](https://github.com/TheMouseNest/Journalator) | Public GitHub repository, default branch `main` | Latest push observed 19 Oct 2026 | Learn actual user transaction/export structures |
| [Auctionator author page](https://www.curseforge.com/wow/addons/auctionator) | Public project page | Retail release observed 13 Oct 2026 | Current supported addon/release information |

The Auctionator project's linked GitHub wiki returned 404. A working current source repository was not verified; do not report source-code coverage from that link. Journalator's old `Auctionator/Journalator` source link redirects to `TheMouseNest/Journalator`.

## Current community observations worth testing

These are first-person community reports or discussions, **not verified Proudmoore prices or guaranteed strategies**.

### 30 October: concentration crafting can reduce login frequency

Source: [“How do I make gold” — conc crafting](https://www.reddit.com/r/woweconomy/comments/1xjhf0v/how_do_i_make_gold_conc_crafting/), found in the current RSS feed and readable through web search/open.

The author describes batching crafts around a replenished concentration bar, consolidating inputs in the warbank and outputs on one seller. Crucially, comments clarify that the post's illustrative gold figures were **hypothetical**, while another participant reports lower results. Treat this as a workflow hypothesis, not an earnings forecast.

Test: for the user's actual professions, knowledge, tools, and learned recipes, compare full input cost and guaranteed output quality against conservative output proceeds after fees. Measure concentration consumed, realized sales, setup cost, and all session time. Without those character details, this cannot become an instruction to buy materials or switch professions. An alt army would add substantial setup and management outside the single-Hunter/15-minute brief.

### 25–26 October: supply changes can invalidate older recipes and price anchors

Source: [Returning after six years](https://www.reddit.com/r/woweconomy/comments/1xf4znf/returning_after_6_years_what_strategy_would_you/). Participants describe current recipe/reagent price compression and remind readers that commodities share a US-wide market.

Test: compare the most recent seven-day commodity price slope and quantity trend with the scanner's older reference prices. A large apparent discount during persistent deflation should be rejected or reduced rather than treated as mean reversion. Verify claimed recipe/drop changes against official patch notes before changing assumptions. The discussion supplies no executable Proudmoore buy quote.

### 12 October: large commodity market resets can strand capital

Source: [An attempt to corner the Auction House food market?](https://www.reddit.com/r/wow/comments/1x44pk2/an_attempt_to_corner_the_auction_house_food_market/). The poster describes Royal Roast inventory being repriced downward after an attempted corner. Seller identity, quantities, and cost basis are unverified.

Test: reject a strategy that needs buying through the order book to manufacture the projected resale price. Check small-lot exit economics at prevailing supply, avoid total-market reset assumptions, and include declining-price stress tests. This supports a risk filter, not an instruction to trade Royal Roast.

### 29–31 October discussion entry points

- [Weekly Flipping & Sniping Thursdays, 29 Oct](https://www.reddit.com/r/woweconomy/comments/1xig1gi/weekly_flipping_sniping_thursdays/): title/date/link verified in RSS; full discussion was not fetched by the web tool during this check.
- [Weekly I Screwed Up Saturday, 31 Oct](https://www.reddit.com/r/woweconomy/comments/1xk6k59/weekly_i_screwed_up_saturday/): title/date/link verified in RSS. Useful for discovering failure modes; not a price source.

## Provider methodology worth adopting

[Saddlebag's own guide](https://saddlebagexchange.com/blog/r3) distinguishes measured changes in listed quantity from regional TSM sales estimates. Supply falls can reflect cancellations and expirations as well as purchases. Its older enchant examples should not be copied into a 2026 trade list. Use the general method: investigate price/quantity history, compare several independent demand indicators, avoid suspected manipulated supply, and trade small quantities.

[Saddlebag's access announcement](https://saddlebagexchange.com/blog/guides/premium-website-pages) says many tools require Discord/supporter access, with some exceptions. Public docs and guides do not authorize bypassing a logged-in analytics page. The inspected OpenAPI declared no security scheme, but that alone does not establish that every operation is free or unauthenticated.

[Journalator's own README](https://github.com/TheMouseNest/Journalator) documents purchase/sale/posting/vendor tracking and exports. These records are the eventual ground truth for this user's profit and elapsed inventory time. They must remain private and cannot be obtained from a cloud feed while the gaming PC is off.

## Converting posts into concrete daily instructions

1. Store a short claim with source permalink, author, post date, game version, market scope, recipe/item IDs where known, and an explicit expiry date. Label opinion, hypothetical numbers, and promotional posts.
2. Translate it into a falsifiable test: e.g. “commodity X's buyable cost is below its static vendor reference” or “recipe Y retains at least Z net profit with the user's actual concentration cost.”
3. Verify against current numerical data: correct Retail build, correct quality/variant, correct US commodity or Proudmoore realm scope, source timestamp, quantity at the proposed price, costs, owned inventory, and spending limits. Community enthusiasm cannot replace any of these checks.
4. Only a passing test may produce an instruction card: **exact item/quality, maximum unit price, maximum total quantity/cost, specific exit route and minimum proceeds, expiry, reason, source, remaining budget**. Otherwise publish the reason to skip, not an invented actionable trade.
5. Reconcile Journalator results and manual session time. Retire an idea after misses, adverse price movement, or excessive reposting. Keep the whole routine within the user's 15-minute cap; research and data collection run unattended.

Recommended collection: poll permitted public feeds conservatively (daily or every six hours), honor caching and Retry-After, bound retained posts, deduplicate by permalink, and store short summaries/links rather than republishing discussions. Search indexed Reddit posts for targeted follow-up reading when permitted. No posts, comments, external messages, or logged-in community actions were performed.

Being useful on Proudmoore means building and checking market-specific records over time. Community reading can propose ideas and expose mistakes; it does not confer a guaranteed expert edge or establish a 300,000g/month result.
