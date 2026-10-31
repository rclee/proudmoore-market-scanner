"""Short-horizon trading checks for the user's allocated 200,000g bankroll."""

from datetime import datetime, timedelta
from decimal import Decimal

from scanner.data import timestamp
from scanner.engine import max_buy_price


def trading_plan(report: dict, extra: dict, now: datetime) -> dict:
    config = report.get("config", {})
    bankroll = config.get("budget_gold", 200000) * 10000
    reserve = config.get("reserve_gold", 40000) * 10000
    session = min(40000 * 10000, max(0, bankroll - reserve))
    policy = {"bankroll_copper": bankroll, "reserve_copper": reserve,
              "session_cap_copper": session, "position_cap_copper": config.get("max_item_exposure_gold", 20000) * 10000,
              "horizon_days": 7, "maximum_hold_hours": 48, "posting_duration_hours": 12,
              "minimum_lot_profit_copper": 100 * 10000, "maximum_tasks": 3,
              "auction_cut_bps": config.get("auction_cut_bps", 500),
              "deposit_allowance_unit_copper": config.get("lost_deposit_allowance_gold", 1) * 10000}
    plan = {"generated_at": now.isoformat(), "policy": policy, "quote_checks": [],
            "status": "data_required", "reason": "Collect starting cash/inventory and live whole-lot quotes before buying"}
    if report.get("mode") != "live" or report.get("status") != "watch_only":
        return plan
    if not config or not report.get("watchlist"):
        return plan
    leads = {row["item_id"]: row for row in report["watchlist"] if row["scope"] == "commodities"}
    candidates = []
    for detail in extra.get("commodity_details", []):
        lead = leads.get(detail["item_id"])
        if (not lead or detail["status"] != "fresh" or detail["total_quantity"] < 100
                or timestamp(detail["observed_at"]) > now + timedelta(minutes=5)
                or now - timestamp(detail["observed_at"]) > timedelta(hours=2)
                or now - timestamp(lead["regional_source_time"]) > timedelta(hours=48)
                or now - timestamp(lead["source_time"]) > timedelta(hours=6)):
            continue
        volume = Decimal(lead["regional_sold_per_day"])
        rate = Decimal(lead["regional_sale_rate"])
        if volume < 100 or rate < Decimal("0.2"):
            continue
        history = sorted(point["median_copper"] for point in detail["history"]
                         if now - timedelta(days=7) <= timestamp(point["at"]) <= now and point["median_copper"] > 0)
        if len(history) < 24:
            continue
        resale = min(lead["conservative_resale_copper"], detail["median_copper"] * 90 // 100,
                     history[len(history) // 4] * 90 // 100)
        deposit = policy["deposit_allowance_unit_copper"]
        maximum = min(config["max_unit_cost_gold"] * 10000,
                      max_buy_price(resale, policy["auction_cut_bps"], config["minimum_return_bps"], deposit))
        profit_per_unit = resale * (10000 - policy["auction_cut_bps"]) // 10000 - maximum - deposit
        if maximum <= 0 or profit_per_unit <= 0:
            continue
        maximum_quantity = min(200, int(volume * Decimal("0.10")), detail["total_quantity"] // 100,
                               policy["position_cap_copper"] // maximum)
        needed = (policy["minimum_lot_profit_copper"] + profit_per_unit - 1) // profit_per_unit
        if needed > maximum_quantity or needed <= 0:
            continue
        quantity = maximum_quantity
        ceiling = maximum * quantity
        candidates.append({"item_id": lead["item_id"], "name": lead["name"], "kind": "auction_resale_quote",
            "quantity": quantity, "maximum_unit_copper": maximum, "maximum_total_copper": ceiling,
            "post_unit_copper": resale, "minimum_post_unit_copper": (maximum + deposit) * 10000 // (10000 - policy["auction_cut_bps"]) + 1,
            "projected_profit_at_cap_copper": profit_per_unit * quantity,
            "snapshot_unit_copper": detail["unit_price_copper"], "snapshot_at": detail["observed_at"],
            "regional_sold_per_day": str(volume), "regional_sale_rate": str(rate),
            "history_samples": len(history), "maximum_hold_hours": 48, "posting_duration_hours": 12,
            "quote_required": True, "sale_guaranteed": False,
            "snapshot_within_limit": detail["unit_price_copper"] <= maximum})
    candidates.sort(key=lambda row: (not row["snapshot_within_limit"], row["snapshot_unit_copper"] / row["maximum_unit_copper"],
                                     -row["projected_profit_at_cap_copper"]))
    remaining = session
    for item in candidates:
        if item["maximum_total_copper"] > remaining:
            continue
        plan["quote_checks"].append(item)
        remaining -= item["maximum_total_copper"]
        if len(plan["quote_checks"]) == 3:
            break
    if plan["quote_checks"]:
        plan["status"] = "collect_quotes"
        plan["reason"] = "Check exact live totals; these are conditional resale experiments, not guaranteed sales"
    return plan
