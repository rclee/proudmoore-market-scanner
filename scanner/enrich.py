"""Add credential-free vendor references, commodity history, and token prices.

Run after the core scan. Extra providers can fail independently without hiding
the original research report. No snapshot becomes an executable buy quote.
"""

import argparse
import csv
import html
import io
import json
import re
import time
import sqlite3
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from scanner.data import FeedError, fetch_feed, number, timestamp
from scanner.report import write_reports

MARKET = "retail-commodities.normal.neutral.us"
TOKEN_URL = "https://data.wowtoken.app/v2/current/retail.json"
CATALOG_URL = "https://wago.tools/"
AHLEDGER = "https://api.ahledger.com/v1"


def download(url: str, limit: int = 4 * 1024 * 1024) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ProudmooreMarketResearch/0.2"})
    with urllib.request.urlopen(request, timeout=20) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise FeedError("Supplemental response exceeds size limit")
    return content


def integer(value, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise FeedError(f"Invalid {field}")
    return value


def source_time(value: str, now: datetime) -> str:
    parsed = timestamp(value)
    if parsed > now + timedelta(minutes=5):
        raise FeedError("Supplemental source timestamp is in the future")
    return parsed.isoformat()


def live_build(content: str) -> str:
    match = re.search(r'data-page="([^"]+)"', content)
    if not match:
        raise FeedError("Live Retail build metadata missing")
    props = json.loads(html.unescape(match.group(1)))["props"]
    product = props["products"]["wow"]
    if product["name"] != "Retail" or product["flavor"] != "_retail_":
        raise FeedError("Build product is not live Retail")
    builds = [row["version"] for row in props["versions"] if row["product"] == "wow"]
    if len(builds) != 1 or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", builds[0]):
        raise FeedError("Ambiguous live Retail build")
    return builds[0]


def parse_catalog(content: str) -> tuple[dict, int]:
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    required = {"ID", "SellPrice", "InventoryType", "Stackable",
                "PlayerLevelToItemLevelCurveID", "ItemLevelOffsetCurveID"}
    if not required.issubset(reader.fieldnames or []):
        raise FeedError("Unsupported vendor-reference CSV schema")
    values = {}
    count = 0
    seen = set()
    for row in reader:
        count += 1
        item = int(number(row["ID"], "ID", integer=True))
        if item <= 0 or item in seen:
            raise FeedError("Duplicate or invalid catalog identity")
        seen.add(item)
        numeric = {key: int(number(row[key], key, integer=True)) for key in required - {"ID"}}
        # Never apply base equipment/scaling values to an auction variant.
        if (numeric["InventoryType"] == 0 and numeric["Stackable"] > 1
                and numeric["PlayerLevelToItemLevelCurveID"] == 0
                and numeric["ItemLevelOffsetCurveID"] == 0):
            values[str(item)] = numeric["SellPrice"]
    if count == 0:
        raise FeedError("Empty vendor catalog")
    return values, count


class Cache:
    """Supplemental cache shares the already-validated scanner history file."""

    def __init__(self, path: Path):
        self.path = path
        # Do not initialize a missing history DB from an enrichment-only run.
        if not path.is_file() or path.stat().st_size < 100:
            raise FeedError("Core history database required before enrichment")
        with closing(sqlite3.connect(path)) as database, database:
            if database.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise FeedError("Unsupported history format")
            database.execute("CREATE TABLE IF NOT EXISTS supplemental_cache (key TEXT PRIMARY KEY, payload TEXT)")

    def get(self, key: str, now: datetime, hours: int) -> dict | None:
        with closing(sqlite3.connect(self.path)) as database:
            row = database.execute("SELECT payload FROM supplemental_cache WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        age = (now - timestamp(data["fetched_at"])).total_seconds()
        return data if 0 <= age <= hours * 3600 else None

    def put(self, key: str, value: dict) -> None:
        with closing(sqlite3.connect(self.path)) as database, database:
            database.execute("INSERT OR REPLACE INTO supplemental_cache VALUES (?,?)", (key, json.dumps(value)))


def vendor_catalog(cache: Cache, now: datetime) -> dict:
    build_data = cache.get("live-build", now, 4)
    if build_data is None:
        build_data = {"build": live_build(download(CATALOG_URL).decode("utf-8")), "fetched_at": now.isoformat()}
        cache.put("live-build", build_data)
    build = build_data["build"]
    data = cache.get("vendor-catalog", now, 24)
    if data is None or data["build"] != build:
        url = f"https://wago.tools/db2/ItemSparse/csv?build={build}"
        values, count = parse_catalog(download(url, limit=64 * 1024 * 1024).decode("utf-8-sig"))
        data = {"build": build, "url": url, "fetched_at": now.isoformat(), "values": values,
                "catalog_rows": count, "stable_stackable_rows": len(values)}
        cache.put("vendor-catalog", data)
    return data


def parse_token(payload: dict, now: datetime) -> dict:
    if not isinstance(payload, dict):
        raise FeedError("Unexpected token response shape")
    value = payload["us"]
    if not isinstance(value, list) or len(value) != 2:
        raise FeedError("Unexpected token-price response")
    observed = source_time(value[0], now)
    price = integer(value[1], "US token gold price", 1)
    fresh = (now - timestamp(observed)).total_seconds() <= 2 * 3600
    return {"status": "fresh" if fresh else "stale", "region": "us", "game": "retail",
            "price_copper": price * 10000, "observed_at": observed, "fetched_at": now.isoformat(),
            "source": "wowtoken.app", "source_url": TOKEN_URL}


def parse_commodity(payload: dict, item_id: int, now: datetime) -> dict:
    if (not isinstance(payload, dict) or not isinstance(payload.get("item"), dict)
            or not isinstance(payload.get("attribution"), dict) or not isinstance(payload.get("series"), list)):
        raise FeedError("Unexpected commodity response shape")
    if payload["market"] != MARKET or payload["item"]["id"] != item_id:
        raise FeedError("Supplemental market or item identity mismatch")
    latest = payload["latest"]
    if not isinstance(latest, dict):
        raise FeedError("No commodity snapshot available")
    observed = source_time(latest["observedAt"], now)
    fields = {name: integer(latest[name], name) for name in ("minBuyout", "median", "quantity", "auctions")}
    points = []
    for row in payload["series"]:
        observed_point = source_time(row["t"], now)
        if timestamp(observed_point) < now - timedelta(days=8):
            continue
        points.append({"at": observed_point, "min_copper": integer(row["min"], "historical minimum"),
                       "median_copper": integer(row["median"], "historical median"),
                       "quantity": integer(row["quantity"], "historical quantity")})
    points.sort(key=lambda row: row["at"])
    if len({row["at"] for row in points}) != len(points):
        raise FeedError("Duplicate history timestamps")
    fresh = (now - timestamp(observed)).total_seconds() <= 2 * 3600
    attribution = payload["attribution"]["url"]
    parsed_url = urlsplit(attribution)
    if parsed_url.scheme != "https" or parsed_url.hostname != "ahledger.com":
        raise FeedError("Unexpected attribution host")
    return {"item_id": item_id, "name": str(payload["item"]["name"]), "market": MARKET,
            "status": "fresh" if fresh else "stale", "observed_at": observed,
            "fetched_at": now.isoformat(), "unit_price_copper": fields["minBuyout"],
            "median_copper": fields["median"], "total_quantity": fields["quantity"],
            "auction_count": fields["auctions"], "history": points[-192:],
            "source": "AHledger", "source_url": f"{AHLEDGER}/prices/{MARKET}/{item_id}?range=7d",
            "attribution_url": attribution,
            "quantity_at_minimum": None, "executable_quote": False}


def community_feed(content: bytes, provider: str, url: str, now: datetime) -> dict:
    root = ET.fromstring(content)
    atom = {"a": "http://www.w3.org/2005/Atom"}
    entries = []
    if root.tag == "{http://www.w3.org/2005/Atom}feed":
        for row in root.findall("a:entry", atom):
            link = row.find("a:link", atom)
            entries.append({"title": row.findtext("a:title", default="", namespaces=atom),
                "url": link.get("href", "") if link is not None else "",
                "published_at": row.findtext("a:published", default="", namespaces=atom)})
    elif root.tag == "rss":
        from email.utils import parsedate_to_datetime
        for row in root.findall("channel/item"):
            entries.append({"title": row.findtext("title", ""), "url": row.findtext("link", ""),
                "published_at": parsedate_to_datetime(row.findtext("pubDate", "")).isoformat()})
    else:
        raise FeedError("Unsupported community feed")
    allowed = "www.reddit.com" if provider == "r/woweconomy" else "blog.tradeskillmaster.com"
    valid = []
    for entry in entries:
        link = urlsplit(entry["url"])
        if link.scheme != "https" or link.hostname != allowed or not entry["title"].strip():
            continue
        published = source_time(entry["published_at"], now)
        valid.append({"title": entry["title"][:250], "url": entry["url"], "published_at": published,
                      "age_days": max(0, (now - timestamp(published)).days), "use": "research_lead_only"})
    return {"provider": provider, "source_url": url, "status": "available",
            "fetched_at": now.isoformat(), "entries": valid[:5]}


def daily_brief(candidates: list[dict], now: datetime) -> dict:
    """Conditional vendor instructions, never an instruction to buy from a snapshot."""
    remaining = 1000 * 10000
    tasks = []
    for item in candidates:
        cross = item.get("snapshot_cross_check", {})
        vendor = item.get("corroborated_vendor_copper")
        if (cross.get("status") != "fresh" or not vendor or item.get("screen_result") != "reference_discount_persists"):
            continue
        ceiling = vendor * 80 // 100
        if ceiling <= 0 or cross["unit_price_copper"] > ceiling:
            continue
        # Small lots, enough to clear 10g at the worst permitted purchase total.
        quantity = (100000 + (vendor - ceiling) - 1) // (vendor - ceiling)
        cap = min(ceiling * quantity, vendor * quantity - 100000, remaining, 4000 * 10000)
        if quantity > 200 or quantity > cross["total_quantity"] or cap < ceiling * quantity or cap <= 0:
            continue
        tasks.append({"item_id": item["item_id"], "name": item["name"], "quantity_to_quote": quantity,
            "maximum_total_copper": cap, "reference_vendor_unit_copper": vendor,
            "minimum_conditional_profit_copper": vendor * quantity - cap,
            "snapshot_at": cross["observed_at"], "status": "conditional_check",
            "buy_without_live_verification": False})
        remaining -= cap
        if len(tasks) == 3:
            break
    instructions = ["Collect mail from your own completed sales.",
                    "Make no new purchases: no corroborated lot passed today's checks.",
                    "Log off; there is no reason to spend the full 15 minutes."] if not tasks else [
                "Collect only mail from your own completed trades; do not buy unrelated items.",
                "For each listed check: verify the exact item's vendor payout and request the stated quantity in game.",
                "Buy manually only if the final full-lot quote is at or below its cap and the vendor payout matches; otherwise skip it.",
                "Collect purchased items, sell those checked items to an NPC vendor, record the result, then log off by 15 minutes."]
    return {"generated_at": now.isoformat(), "time_limit_minutes": 15, "session_cap_copper": 10000000,
            "status": "conditional_checks" if tasks else "skip", "tasks": tasks,
            "instructions": instructions,
            "reason": "No current, corroborated vendor-reference lot fits the limits" if not tasks
                      else "Snapshot references suggest checks; quantities at the quoted price and live NPC proceeds remain unverified"}


def enrich_report(report: dict, cache: Cache, now: datetime) -> dict:
    deadline = time.monotonic() + 180
    extra = {"generated_at": now.isoformat(), "commodity_details": [], "vendor_candidates": [], "errors": []}
    if report.get("mode") != "live" or report.get("status") not in ("watch_only", "stale"):
        return {**extra, "status": "unavailable"}
    try:
        extra["token"] = parse_token(json.loads(download(TOKEN_URL)), now)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        extra["errors"].append({"source": "wowtoken.app", "message": str(exc)})
    catalog = None
    commodity_feed = None
    try:
        catalog = vendor_catalog(cache, now)
        # Full commodity universe, including items that failed speculative sales filters.
        commodity_feed = fetch_feed("commodities", "https://public-data.tradeskillmaster.com/retail/us/commodities.csv", now)
        matched = sum(str(row["itemId"]) in catalog["values"] for row in commodity_feed.rows)
        positive = sum(catalog["values"].get(str(row["itemId"]), 0) > 0 for row in commodity_feed.rows)
        catalog_fresh = (now - timestamp(catalog["fetched_at"])).total_seconds() <= 24 * 3600
        extra["vendor_catalog"] = {key: value for key, value in catalog.items() if key != "values"}
        extra["vendor_catalog"].update({"source": "Wago client DB2", "matched_commodities": matched,
            "positive_vendor_references": positive, "commodity_count": len(commodity_feed.rows),
            "commodity_scan_at": commodity_feed.source_time,
            "status": "reference_only" if catalog_fresh else "stale", "live_vendor_verified": False})
        for item in commodity_feed.rows:
            vendor = catalog["values"].get(str(item["itemId"]), 0)
            buy = item["minBuyout"]
            if (item["name"].strip() and vendor > 0 and 0 < buy <= vendor * 80 // 100
                    and buy <= report["config"]["max_unit_cost_gold"] * 10000):
                extra["vendor_candidates"].append({"item_id": item["itemId"], "name": item["name"],
                    "reference_vendor_copper": vendor, "snapshot_buy_copper": buy,
                    "spread_per_unit_copper": vendor - buy, "source_time": commodity_feed.source_time,
                    "build": catalog["build"], "status": "reference_only", "recommended_quantity": 0})
        extra["vendor_candidates"].sort(key=lambda row: -row["spread_per_unit_copper"])
        extra["vendor_catalog"]["below_reference_count"] = len(extra["vendor_candidates"])
        extra["vendor_candidates"] = extra["vendor_candidates"][:10]
    except (ValueError, KeyError, TypeError, OSError, csv.Error) as exc:
        extra["errors"].append({"source": "Wago vendor references", "message": str(exc)})
    # Bounded documented API reads, far below the provider's 300/minute limit.
    ids = [row["item_id"] for row in extra["vendor_candidates"]]
    ids += [row["item_id"] for row in report["watchlist"] if row["scope"] == "commodities"][:5]
    ids = list(dict.fromkeys(ids))[:15]
    lookup = {row["item_id"]: row for row in extra["vendor_candidates"]}
    for item_id in ids:
        if time.monotonic() >= deadline:
            extra["errors"].append({"source": "AHledger", "message": "Supplemental time budget reached; remaining requests skipped"})
            break
        try:
            url = f"{AHLEDGER}/prices/{MARKET}/{item_id}?range=7d"
            detail = parse_commodity(json.loads(download(url)), item_id, now)
            if catalog and str(item_id) in catalog["values"]:
                detail["reference_vendor_copper"] = catalog["values"][str(item_id)]
                detail["vendor_build"] = catalog["build"]
            extra["commodity_details"].append(detail)
            if item_id in lookup:
                lookup[item_id]["snapshot_cross_check"] = {
                    "status": detail["status"], "unit_price_copper": detail["unit_price_copper"],
                    "total_quantity": detail["total_quantity"], "observed_at": detail["observed_at"]}
                reference = lookup[item_id]["reference_vendor_copper"]
                if detail["status"] != "fresh":
                    lookup[item_id]["screen_result"] = "newer_snapshot_stale"
                    continue
                if detail["unit_price_copper"] <= 0 or detail["unit_price_copper"] > reference * 80 // 100:
                    lookup[item_id]["screen_result"] = "newer_price_rejects_discount"
                    continue
                lookup[item_id]["screen_result"] = "vendor_corroboration_missing"
                item_data = json.loads(download(f"{AHLEDGER}/items/{item_id}?game=retail"))
                if item_data["id"] != item_id:
                    raise FeedError("Vendor corroboration item mismatch")
                alternate_vendor = integer(item_data["vendorSell"], "corroborating vendor reference")
                lookup[item_id]["corroborating_vendor_copper"] = alternate_vendor
                if alternate_vendor != reference:
                    result = "vendor_sources_disagree"
                elif detail["status"] != "fresh":
                    result = "newer_snapshot_stale"
                elif detail["unit_price_copper"] <= 0 or detail["unit_price_copper"] > reference * 80 // 100:
                    result = "newer_price_rejects_discount"
                else:
                    result = "reference_discount_persists"
                    lookup[item_id]["corroborated_vendor_copper"] = reference
                lookup[item_id]["screen_result"] = result
        except OSError as exc:
            extra["errors"].append({"source": f"AHledger item {item_id}", "message": str(exc)})
            # A missing individual item is local to that record. Rate limits,
            # outages, and timeouts stop this provider for the current run.
            if not isinstance(exc, urllib.error.HTTPError) or exc.code != 404:
                break
        except (ValueError, KeyError, TypeError) as exc:
            extra["errors"].append({"source": f"AHledger item {item_id}", "message": str(exc)})
    extra["status"] = "partial" if extra["errors"] else "available"
    extra["daily_brief"] = daily_brief(extra["vendor_candidates"], now)
    extra["community"] = []
    for provider, url in (("r/woweconomy", "https://www.reddit.com/r/woweconomy/new/.rss"),
                          ("TSM Blog", "https://blog.tradeskillmaster.com/feed/")):
        try:
            cached_feed = cache.get("community:" + provider, now, 1)
            if cached_feed is None:
                cached_feed = community_feed(download(url), provider, url, now)
                cache.put("community:" + provider, cached_feed)
            extra["community"].append(cached_feed)
        except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as exc:
            extra["community"].append({"provider": provider, "source_url": url, "status": "unavailable",
                                        "fetched_at": now.isoformat(), "entries": [], "message": str(exc)})
    if any(feed["status"] != "available" for feed in extra["community"]):
        extra["status"] = "partial"
    return extra


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path("state/market.sqlite3"))
    parser.add_argument("--output", type=Path, default=Path("output/live"))
    args = parser.parse_args()
    report = json.loads((args.output / "report.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    try:
        report["enrichment"] = enrich_report(report, Cache(args.state), now)
    except (ValueError, OSError, sqlite3.Error) as exc:
        report["enrichment"] = {"status": "unavailable", "generated_at": now.isoformat(),
                                "errors": [{"source": "supplemental cache", "message": str(exc)}]}
    write_reports(args.output, report)
    summary = report["enrichment"]
    print(json.dumps({"status": summary["status"], "vendor_coverage": summary.get("vendor_catalog", {}),
                      "commodity_details": len(summary.get("commodity_details", [])), "errors": summary.get("errors", [])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
