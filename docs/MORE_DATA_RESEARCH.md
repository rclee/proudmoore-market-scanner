# Additional Retail market data — verified 31 October 2026

## Implementable route

Use a **pinned Retail ItemSparse export** for broad vendor-value enrichment, then bounded **AHledger US commodity requests** for independent snapshot quantities and history. Neither tested source required a key. These are reference/snapshot data, not executable buy quotes or a guarantee that a merchant will pay a particular amount for an exact item.

## Wago.Tools: static vendor metadata

Verified export: [ItemSparse CSV, build 12.1.5.70688](https://wago.tools/db2/ItemSparse/csv?build=12.1.5.70688).

- HTTP 200; actual `text/csv; charset=UTF-8`, not challenge HTML.
- 51,698,117 bytes; 175,787 records.
- `Cache-Control: max-age=14400`; `Last-Modified: Sat, 31 Oct 2026 11:43:52 GMT`; no ETag observed.
- Local verified copy: `output/itemsparse-live.csv` (ignored by Git).
- Relevant fields: `ID`, `Display_lang`, `SellPrice`, `BuyPrice`, `VendorStackCount`, `InventoryType`, `Stackable`, `ItemLevel`, `PlayerLevelToItemLevelCurveID`, `ItemLevelOffsetCurveID`, `ItemLevelOffsetItemLevel`, `Flags_0` through `Flags_4`.

**Do not use the export's default build.** The default ItemSparse page selected `12.1.7.70668`, a PTR build. On the [Wago homepage](https://wago.tools/), parse the HTML `data-page` attribute, HTML-unescape it, decode JSON, and select `props.versions` entry with `product == "wow"`. `props.products.wow` identifies Retail / `_retail_`. The [build listing](https://wago.tools/builds) independently identified `12.1.5.70688` as product `wow`, processed, not background-download, description `WOW-70688patch12.1.5_Retail`.

Observed samples (copper): Linen Cloth 2589 `SellPrice=13`; Infinite Dust 34054 `0`; Unraveled Instructions 225672 `1000`. All had inventory type 0 and both inspected level curves 0. `PriceRandomValue` was non-1 even for Linen Cloth, so requiring it to equal 1 would discard otherwise useful commodity records. Start by joining only item IDs confirmed as commodities by the existing TSM commodity feed; exclude equipment/scaling cases and retain exact build provenance. Static base item values may miss server hotfixes or contextual modifiers.

Access/permission limit: public CSV downloads worked normally. No explicit bulk-data/API license or published rate policy was verified; `/terms`, `/terms-of-service`, and `/about` returned 404. [robots.txt](https://wago.tools/robots.txt) disallows general crawling except the homepage. Do not describe a broad crawling permission as established. Prefer one cached export per build, conservative refreshes, and provider attribution. Column definitions can be inspected in the schema project's own [ItemSparse definition](https://github.com/wowdev/WoWDBDefs/blob/master/definitions/ItemSparse.dbd).

## AHledger: bounded commodity enrichment

[Provider API documentation](https://ahledger.com/developers) permits personal/commercial use with linked attribution, prohibits claiming its observations as your own or reselling its feed, and asks clients to honor caching. General limit: 300 requests/minute per address; market-tool endpoints: 60/minute. Retain returned attribution links. Bulk exports beyond the documented surface require contacting the provider.

Verified HTTP 200 responses:

- [Markets](https://api.ahledger.com/v1/markets): includes `retail-commodities.normal.neutral.us`. Its single realm Retail market was labelled **Tichondrius**, so never substitute it for Proudmoore.
- [Retail item 2589](https://api.ahledger.com/v1/items/2589?game=retail): `vendorSell=13`, name/class/subclass/level/icon and attribution. Also verified 34054=0 and 225672=1000. Cache: 300 seconds.
- [US commodity Linen Cloth history](https://api.ahledger.com/v1/prices/retail-commodities.normal.neutral.us/2589?range=7d): source `Blizzard API`, timestamped price/median, quantity/auction counts, historical medians, and hourly series. Cache observed: 60 seconds browser / 300 seconds shared.

An observed quantity describes the snapshot's total supply, not units available at its minimum price. Null sales estimates remain unknown. Base item vendor metadata does not establish variant-specific gear value. The provider describes item/vendor provenance on its [About page](https://ahledger.com/about).

## Undermine Exchange: useful, but needs a user key

[Official provider documentation](https://undermine.exchange/api.html) offers Retail price/quantity histories and item-level pricing. Every API request requires a key obtained through Patreon sign-in, even free endpoints. The documented hourly budget is 3,000 weighted points. Vendor/item metadata is explicitly outside its API. It therefore cannot close the vendor-value gap without additional data and cannot be connected credential-free.

## Blizzard: authoritative next integration

The [Battle.net developer portal](https://community.developer.battle.net/documentation/world-of-warcraft/game-data-apis) is the official source for item and auction data. A client-credentials OAuth setup is needed. Existing public-source coverage can improve immediately without waiting for these credentials, while retaining an upgrade path for Proudmoore auction depth and exact item modifiers.
