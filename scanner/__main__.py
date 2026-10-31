"""Run with python -m scanner. Live is the default; demo never touches live history."""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from scanner.data import FeedError, fetch_feed, number, parse_feed, record_history
from scanner.engine import build_watchlist
from scanner.report import write_reports


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("region") != "us" or config.get("realm") != "proudmoore":
        raise FeedError("This milestone supports only Proudmoore-US Retail")
    integer_fields = ("budget_gold", "reserve_gold", "max_unit_cost_gold", "max_item_exposure_gold",
                      "minimum_return_bps", "auction_cut_bps", "resale_markdown_bps",
                      "lost_deposit_allowance_gold", "market_max_age_hours", "region_max_age_hours",
                      "history_days", "max_watchlist_items")
    for key in integer_fields:
        if type(config.get(key)) is not int or config[key] < 0:
            raise FeedError(f"Invalid nonnegative integer config: {key}")
    if (config["reserve_gold"] >= config["budget_gold"] or config["auction_cut_bps"] >= 10000
            or config["resale_markdown_bps"] >= 10000 or not 1 <= config["max_watchlist_items"] <= 100
            or not 1 <= config["history_days"] <= 35
            or min(config["market_max_age_hours"], config["region_max_age_hours"],
                   config["max_unit_cost_gold"], config["max_item_exposure_gold"]) <= 0):
        raise FeedError("Invalid config limits")
    if number(config["minimum_sale_rate"], "minimum_sale_rate") > Decimal(1):
        raise FeedError("minimum_sale_rate must be between zero and one")
    number(config["minimum_sold_per_day"], "minimum_sold_per_day")
    return config


def demo_feeds(now: datetime) -> list:
    """Synthetic records have invented item IDs and are never real market quotes."""
    scan = (now - timedelta(minutes=30)).isoformat()
    market_header = "itemId,name,marketValue,minBuyout,recent,historical,updatedAt\n"
    region_header = "itemId,name,marketValue,historical,avgSalePrice,saleRate,soldPerDay,updatedAt\n"
    data = {
        "realm": market_header + f"900001,Demo ceremonial blade,12000000,5000000,11500000,11000000,{scan}\n",
        "commodities": market_header + f"900002,Demo gleaming ore,1000000,400000,950000,900000,{scan}\n",
        "region": region_header + f"900001,Demo ceremonial blade,12000000,11000000,10000000,0.2,3,{scan}\n"
        + f"900002,Demo gleaming ore,1000000,900000,850000,0.4,100,{scan}\n",
    }
    return [parse_feed(scope, "synthetic://demo/" + scope, contents, now) for scope, contents in data.items()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--state", type=Path, default=Path("state/market.sqlite3"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)
    output = args.output or Path("output/demo" if args.demo else "output/live")
    now = datetime.now(timezone.utc)
    report = {"generated_at": now.isoformat(), "mode": "demo" if args.demo else "live",
              "status": "unavailable", "feeds": [], "watchlist": [], "actionable_buy_count": 0}
    try:
        config = load_config(args.config)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report["error"] = f"Configuration error: {exc}"
        write_reports(output, report)
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    report["config"] = config
    code = 0
    try:
        if args.demo:
            feeds = demo_feeds(now)
        else:
            base = "https://public-data.tradeskillmaster.com/retail/us/"
            endpoints = {"realm": base + "realm/proudmoore/items.csv",
                         "commodities": base + "commodities.csv", "region": base + "region/items.csv"}
            feeds = [fetch_feed(scope, url, now) for scope, url in endpoints.items()]
        summaries = [feed.summary(now, config["region_max_age_hours"] if feed.scope == "region"
                                  else config["market_max_age_hours"]) for feed in feeds]
        report["feeds"] = summaries
        report["watchlist"], report["filters"] = build_watchlist(feeds, config, summaries)
        if args.demo:
            report["history"] = {"coverage": "Demo does not read or write live state"}
        else:
            report["history"] = record_history(args.state, feeds, report["watchlist"], now, config["history_days"])
        report["status"] = "demo" if args.demo else ("watch_only" if all(f["fresh"] for f in summaries) else "stale")
        if report["status"] == "stale":
            code = 1
    except (FeedError, UnicodeError, sqlite3.Error, OSError) as exc:
        report["watchlist"] = []
        report["error"] = str(exc)
        code = 1
    write_reports(output, report)
    print(f"{report['status']}: {len(report['watchlist'])} research candidates; 0 actionable buys. Reports: {output.resolve()}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
