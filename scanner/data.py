"""Strict public-feed ingestion and bounded, persistent observation history."""

import csv
import hashlib
import io
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class FeedError(ValueError):
    """The feed cannot safely be interpreted."""


def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise FeedError("Source timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        raise FeedError("Invalid source timestamp") from exc


def number(value: str, field: str, integer: bool = False) -> Decimal:
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise FeedError(f"Invalid {field}") from exc
    if not result.is_finite() or result < 0 or (integer and result != result.to_integral_value()):
        raise FeedError(f"Invalid nonnegative {'integer ' if integer else ''}{field}")
    return result


@dataclass(frozen=True)
class Feed:
    scope: str
    url: str
    columns: list[str]
    rows: list[dict]
    source_time: str
    fetched_at: str
    digest: str

    def summary(self, now: datetime, max_age_hours: int) -> dict:
        age_hours = (now - timestamp(self.source_time)).total_seconds() / 3600
        demand = "saleRate" in self.columns and "soldPerDay" in self.columns
        return {
            "scope": self.scope, "url": self.url, "columns": self.columns,
            "row_count": len(self.rows), "source_time": self.source_time,
            "fetched_at": self.fetched_at, "sha256": self.digest,
            "age_hours": round(age_hours, 2),
            "fresh": -0.0834 <= age_hours <= max_age_hours,
            "demand_fields_present": demand,
            "unnamed_rows": sum(not row["name"].strip() for row in self.rows),
            "positive_demand_rows": sum(
                row.get("saleRate", 0) > 0 and row.get("soldPerDay", 0) > 0
                for row in self.rows
            ) if demand else 0,
        }


def parse_feed(scope: str, url: str, content: str, fetched_at: datetime) -> Feed:
    try:
        return _parse_feed(scope, url, content, fetched_at)
    except csv.Error as exc:
        raise FeedError(f"Invalid {scope} CSV: {exc}") from exc


def _parse_feed(scope: str, url: str, content: str, fetched_at: datetime) -> Feed:
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    columns = list(reader.fieldnames or [])
    required = {"itemId", "name", "marketValue", "historical", "updatedAt"}
    required |= {"avgSalePrice", "saleRate", "soldPerDay"} if scope == "region" else {"minBuyout", "recent"}
    if len(set(columns)) != len(columns) or not required.issubset(columns):
        raise FeedError(f"Unexpected {scope} CSV schema; missing {sorted(required - set(columns))}")
    rows = []
    seen = set()
    scan_times = set()
    for line, source in enumerate(reader, start=2):
        if None in source or any(value is None for value in source.values()):
            raise FeedError(f"Malformed {scope} CSV row {line}")
        row: dict[str, Any] = dict(source)
        for field in ("itemId", "marketValue", "historical", "minBuyout", "recent", "avgSalePrice"):
            if field in row:
                row[field] = int(number(row[field], field, integer=True))
        if row["itemId"] <= 0 or row["itemId"] in seen:
            raise FeedError(f"Invalid/duplicate item identity at {scope} row {line}")
        for field in ("saleRate", "soldPerDay"):
            if field in row:
                row[field] = number(row[field], field)
        if row.get("saleRate", 0) > 1:
            raise FeedError(f"Sale rate outside 0–1 at row {line}")
        scan = timestamp(row["updatedAt"])
        if scan > fetched_at + timedelta(minutes=5):
            raise FeedError(f"Future source scan timestamp at row {line}")
        row["updatedAt"] = scan.isoformat()
        scan_times.add(row["updatedAt"])
        seen.add(row["itemId"])
        rows.append(row)
    if not rows or len(scan_times) != 1:
        raise FeedError(f"Empty {scope} feed or inconsistent scan times")
    return Feed(scope, url, columns, rows, scan_times.pop(), fetched_at.isoformat(),
                hashlib.sha256(content.encode("utf-8")).hexdigest())


def fetch_feed(scope: str, url: str, now: datetime) -> Feed:
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ProudmooreMarketResearch/0.1"})
            with urllib.request.urlopen(request, timeout=45) as response:
                # Bound unexpected responses; normal public files are much smaller.
                body = response.read(64 * 1024 * 1024 + 1)
            if len(body) > 64 * 1024 * 1024:
                raise FeedError(f"Oversized {scope} feed")
            return parse_feed(scope, url, body.decode("utf-8-sig"), now)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == 2:
                raise FeedError(f"Could not download {scope} feed after three attempts") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def record_history(path: Path, feeds: list[Feed], candidates: list[dict], now: datetime, days: int) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.exists()
    if existing and path.stat().st_size < 100:
        raise FeedError("Existing history database is empty or truncated; refusing to reset it")
    with closing(sqlite3.connect(path)) as database, database:
        if existing:
            if (database.execute("PRAGMA quick_check").fetchall() != [("ok",)]
                    or database.execute("PRAGMA user_version").fetchone()[0] != 1):
                raise FeedError("Existing history database failed integrity or format validation")
            for table, columns in {"scans": ["scope", "source_time", "fetched_at", "digest", "row_count"],
                                   "observations": ["scope", "item_id", "source_time", "price"]}.items():
                actual = [row[1] for row in database.execute(f"PRAGMA table_info({table})")]
                if actual != columns:
                    raise FeedError("Existing history database has an unsupported schema")
        database.execute("""CREATE TABLE IF NOT EXISTS scans (
            scope TEXT, source_time TEXT, fetched_at TEXT, digest TEXT, row_count INTEGER,
            PRIMARY KEY(scope, source_time))""")
        database.execute("""CREATE TABLE IF NOT EXISTS observations (
            scope TEXT, item_id INTEGER, source_time TEXT, price INTEGER,
            PRIMARY KEY(scope, item_id, source_time))""")
        database.execute("PRAGMA user_version=1")
        inserted = 0
        new_market_scans = set()
        for feed in feeds:
            prior = database.execute("SELECT digest FROM scans WHERE scope=? AND source_time=?",
                                     (feed.scope, feed.source_time)).fetchone()
            if prior and prior[0] != feed.digest:
                raise FeedError(f"Changed contents for existing {feed.scope} scan timestamp")
            cursor = database.execute("INSERT OR IGNORE INTO scans VALUES (?,?,?,?,?)",
                                      (feed.scope, feed.source_time, feed.fetched_at, feed.digest, len(feed.rows)))
            inserted += cursor.rowcount
            if cursor.rowcount and feed.scope != "region":
                new_market_scans.add((feed.scope, feed.source_time))
        for candidate in candidates:
            if (candidate["scope"], candidate["source_time"]) not in new_market_scans:
                continue
            database.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?)",
                             (candidate["scope"], candidate["item_id"], candidate["source_time"],
                              candidate["observed_buy_copper"]))
        cutoff = (now - timedelta(days=days)).isoformat()
        database.execute("DELETE FROM scans WHERE julianday(source_time) < julianday(?)", (cutoff,))
        database.execute("DELETE FROM observations WHERE julianday(source_time) < julianday(?)", (cutoff,))
        count = database.execute("SELECT count(*) FROM scans").fetchone()[0]
        observations = database.execute("SELECT count(*) FROM observations").fetchone()[0]
        coverage = database.execute("SELECT min(source_time), max(source_time) FROM observations").fetchone()
        database.commit()
        database.execute("VACUUM")
    return {"new_scans": inserted, "retained_scans": count, "retained_observations": observations,
            "first_observation": coverage[0], "last_observation": coverage[1],
            "coverage": "Shortlisted observations only; not complete market or sales history"}
