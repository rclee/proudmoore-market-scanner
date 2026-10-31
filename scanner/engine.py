"""Conservative research filters. This milestone never emits buy recommendations."""

from decimal import Decimal

COPPER_PER_GOLD = 10000


def max_buy_price(resale: int, cut_bps: int, return_bps: int, lost_deposit: int) -> int:
    proceeds = resale * (10000 - cut_bps) // 10000
    return max(0, (proceeds - lost_deposit) * 10000 // (10000 + return_bps))


def build_watchlist(feeds: list, config: dict, summaries: list[dict]) -> tuple[list[dict], dict]:
    regional = {row["itemId"]: row for feed in feeds if feed.scope == "region" for row in feed.rows}
    freshness = {summary["scope"]: summary["fresh"] for summary in summaries}
    candidates = []
    rejected = {"unnamed_item": 0, "no_regional_match": 0, "weak_demand": 0, "missing_prices": 0,
                "over_unit_cap": 0, "insufficient_return": 0}
    deposit = config["lost_deposit_allowance_gold"] * COPPER_PER_GOLD
    unit_cap = config["max_unit_cost_gold"] * COPPER_PER_GOLD
    for feed in feeds:
        if feed.scope == "region":
            continue
        for item in feed.rows:
            if not item["name"].strip():
                rejected["unnamed_item"] += 1
                continue
            demand = regional.get(item["itemId"])
            if not demand:
                rejected["no_regional_match"] += 1
                continue
            if (demand["saleRate"] < Decimal(config["minimum_sale_rate"])
                    or demand["soldPerDay"] < Decimal(config["minimum_sold_per_day"])):
                rejected["weak_demand"] += 1
                continue
            anchors = [item["marketValue"], item["historical"], item["recent"], demand["avgSalePrice"]]
            buy = item["minBuyout"]
            if buy <= 0 or min(anchors) <= 0:
                rejected["missing_prices"] += 1
                continue
            if buy > unit_cap:
                rejected["over_unit_cap"] += 1
                continue
            resale = min(anchors) * (10000 - config["resale_markdown_bps"]) // 10000
            maximum = min(unit_cap, max_buy_price(resale, config["auction_cut_bps"],
                                                 config["minimum_return_bps"], deposit))
            if buy > maximum or maximum == 0:
                rejected["insufficient_return"] += 1
                continue
            profit = resale * (10000 - config["auction_cut_bps"]) // 10000 - buy - deposit
            blockers = ["Current listing price and available quantity not verified",
                        "No verified whitelist or inventory balance",
                        "Regional demand estimate; Proudmoore sell-through unproven",
                        "7–14 day market validation not completed"]
            if feed.scope == "realm":
                blockers.append("Base item CSV does not verify equipment or other item variants")
            if not freshness[feed.scope] or not freshness["region"]:
                blockers.insert(0, "Source data is stale")
            candidates.append({
                "item_id": item["itemId"], "name": item["name"], "scope": feed.scope,
                "market": "US commodities" if feed.scope == "commodities" else "Proudmoore-US items",
                "source_time": feed.source_time, "regional_source_time": demand["updatedAt"],
                "observed_buy_copper": buy, "research_max_buy_copper": maximum,
                "conservative_resale_copper": resale, "projected_profit_copper": profit,
                "return_bps": profit * 10000 // buy,
                "regional_sale_rate": str(demand["saleRate"]),
                "regional_sold_per_day": str(demand["soldPerDay"]),
                "status": "watch_only", "recommended_quantity": 0, "blockers": blockers,
            })
    candidates.sort(key=lambda row: (-row["projected_profit_copper"], row["scope"], row["item_id"]))
    return candidates[:config["max_watchlist_items"]], {"filtered_out": rejected,
            "matching_candidates_before_limit": len(candidates)}
