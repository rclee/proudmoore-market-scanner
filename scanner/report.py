"""Portable reports with no external scripts or account data."""

import html
import json
from datetime import timedelta
from pathlib import Path

from scanner.data import timestamp


def gold(copper: int) -> str:
    return f"{copper / 10000:,.2f}g"


def write_reports(output: Path, report: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    # Replace each file atomically so interrupted writes never leave partial JSON/HTML.
    documents = {"report.json": json.dumps(report, indent=2),
                 "validation.md": validation(report), "index.html": dashboard(report)}
    for name, contents in documents.items():
        temporary = output / (name + ".tmp")
        temporary.write_text(contents, encoding="utf-8")
        temporary.replace(output / name)


def validation(report: dict) -> str:
    lines = ["# Proudmoore market data validation", "", f"Status: **{report['status']}**",
             f"Generated: {report['generated_at']}", "",
             "Research only. No live auction depth, verified variants, inventory, or confirmed trades.", ""]
    if report.get("error"):
        lines.extend([f"Error: {report['error']}", ""])
    for feed in report["feeds"]:
        lines.extend([f"## {feed['scope']}", f"- Source: {feed['url']}",
                      f"- Rows: {feed['row_count']:,}", f"- Upstream scan: {feed['source_time']}",
                      f"- Fetched: {feed['fetched_at']}", f"- Fresh: {feed['fresh']}",
                      f"- Unnamed records (excluded from watchlist): {feed['unnamed_rows']:,}",
                      f"- Columns: {', '.join(feed['columns'])}",
                      f"- Positive regional demand rows: {feed['positive_demand_rows']:,}", ""])
    lines.extend(["## Interpretation", "",
                  "All input prices and calculations use integer copper. Demand fields are TSM regional estimates, not Proudmoore sales.",
                  "The 20% filter means return on purchase cost after configured fees and allowances; it is conditional on a sale.",
                  "Only base item IDs are available in these CSVs. Realm variants require further verification.",
                  "Candidate history is bounded and does not represent complete market history or completed sales.",
                  "No personal transaction data is collected. All recommended quantities are zero.", "",
                  "## History", "", json.dumps(report.get("history", {}), indent=2), "",
                  "## Filters", "", json.dumps(report.get("filters", {}), indent=2), ""])
    if "enrichment" in report:
        extra = report["enrichment"]
        lines.extend(["## Additional sources", "", f"Status: {extra['status']}",
            "Vendor values are pinned Retail client-data references, not verified live NPC payouts.",
            "AHledger quantities describe total snapshot supply, not units at its cheapest price.",
            "Community posts are unverified research leads; they never directly authorize purchases.", "",
            "```json", json.dumps({"vendor_catalog": extra.get("vendor_catalog"), "token": extra.get("token"),
                "commodity_details": len(extra.get("commodity_details", [])),
                "daily_brief": extra.get("daily_brief"),
                "community": [{"provider": f["provider"], "status": f["status"]} for f in extra.get("community", [])],
                "errors": extra.get("errors", [])}, indent=2), "```", "",
            "Sources: [Wago](https://wago.tools/), [AHledger](https://ahledger.com/developers), "
            "[wowtoken.app](https://wowtoken.app/), [r/woweconomy](https://www.reddit.com/r/woweconomy/), "
            "[TSM Blog](https://blog.tradeskillmaster.com/).", ""])
    return "\n".join(lines)


def dashboard(report: dict) -> str:
    escape = html.escape
    if "config" not in report:
        return ('<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Market Watch · Unavailable</title><h1>Market data unavailable</h1><p>'
                + escape(report.get("error", "Configuration unavailable"))
                + '</p><p>No purchases recommended.</p></html>')
    config = report["config"]
    mode = "SYNTHETIC DEMO · NOT LIVE PRICES" if report["mode"] == "demo" else "LIVE FEEDS · RESEARCH ONLY"
    cards = []
    for index, candidate in enumerate(report["watchlist"], 1):
        blockers = "".join(f"<li>{escape(reason)}</li>" for reason in candidate["blockers"])
        cards.append(f"""<article data-scope="{escape(candidate['scope'])}">
<div class="card-top"><span class="rank">{index:02}</span><span class="tag">WATCH ONLY</span></div>
<h3>{escape(candidate['name'])}</h3><p class="muted">{escape(candidate['market'])} · Item {candidate['item_id']}</p>
<div class="prices"><div><small>Snapshot buy price</small><strong>{gold(candidate['observed_buy_copper'])}</strong></div>
<div><small>Research buy ceiling</small><strong>{gold(candidate['research_max_buy_copper'])}</strong></div></div>
<dl><div><dt>Conservative resale</dt><dd>{gold(candidate['conservative_resale_copper'])}</dd></div>
<div><dt>Projected net / unit if sold</dt><dd>{gold(candidate['projected_profit_copper'])}</dd></div>
<div><dt>Return on purchase cost</dt><dd>{candidate['return_bps'] / 100:.1f}%</dd></div>
<div><dt>Regional sale rate estimate</dt><dd>{escape(candidate['regional_sale_rate'])}</dd></div>
<div><dt>Regional sold / day estimate</dt><dd>{escape(candidate['regional_sold_per_day'])}</dd></div>
<div><dt>Recommended purchase</dt><dd>0 units · pending validation</dd></div></dl>
<p class="timestamp">Market scan: {escape(candidate['source_time'])}<br>Demand scan: {escape(candidate['regional_source_time'])}</p>
<details><summary>What still needs checking</summary><ul>{blockers}</ul></details></article>""")
    sources = []
    for feed in report["feeds"]:
        age_limit = config["region_max_age_hours"] if feed["scope"] == "region" else config["market_max_age_hours"]
        expiry = timestamp(feed["source_time"]) + timedelta(hours=age_limit)
        sources.append(f"<li data-expiry='{escape(expiry.isoformat())}'><b>{escape(feed['scope'])}</b>"
                       f"<span>{feed['row_count']:,} rows · {escape(feed['source_time'])}</span>"
                       f"<em>{'Fresh at scan' if feed['fresh'] else 'STALE'}</em></li>")
    error = f"<p>{escape(report['error'])}</p>" if report.get("error") else ""
    empty = "<div class='empty'>No items passed the research filters. Waiting is a valid outcome.</div>" if not cards else ""
    source_html = "".join(sources) or "<li>No validated source data available.</li>"
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Proudmoore · Market Watch</title>
<style>
:root{color-scheme:dark;--bg:#101713;--panel:#19231c;--line:#334136;--text:#edf1e7;--muted:#a9b6a9;--accent:#d2ed91}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,sans-serif}
main{max-width:1160px;margin:auto;padding:36px 24px 60px}.brand{letter-spacing:.18em;font-size:12px;color:var(--accent);font-weight:700}
header{padding:32px 0 24px;border-bottom:1px solid var(--line)}h1{font-size:clamp(34px,6vw,60px);line-height:1.05;letter-spacing:-.045em;margin:12px 0 18px}
.intro{max-width:650px;color:var(--muted)}.notice{margin:24px 0;padding:20px;border:1px solid #8c7942;background:#292719;border-radius:12px;color:#f0dda0}
.notice strong{display:block}.notice p{margin-bottom:0}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:24px 0 36px}
.stat{padding:18px;background:var(--panel);border:1px solid var(--line);border-radius:12px}.stat small{display:block;color:var(--muted)}.stat strong{font-size:26px;font-weight:600}
.section-head{display:flex;gap:12px;justify-content:space-between;align-items:center;flex-wrap:wrap}h2{font-size:24px;margin:0}button{background:transparent;color:var(--text);border:1px solid var(--line);border-radius:20px;padding:8px 14px;cursor:pointer}
button[aria-pressed=true]{background:var(--accent);color:#182011}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:20px}article{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:22px}
.card-top{display:flex;justify-content:space-between;align-items:center}.rank{color:var(--muted);font-size:13px}.tag{font-size:10px;letter-spacing:.12em;color:var(--accent);border:1px solid #526442;padding:4px 8px;border-radius:20px}
h3{font-size:20px;line-height:1.3;margin:18px 0 4px}.muted,.timestamp{color:var(--muted);font-size:12px}.prices{display:grid;grid-template-columns:1fr 1fr;gap:12px;border-top:1px solid var(--line);padding-top:18px;margin-top:22px}
.prices small{display:block;font-size:11px;color:var(--muted)}.prices strong{font-size:19px}dl{font-size:12px;margin:20px 0}dl div{display:flex;justify-content:space-between;gap:12px;padding:6px 0}dt{color:var(--muted)}dd{margin:0;text-align:right}
details{border-top:1px solid var(--line);padding-top:14px;font-size:12px;color:var(--muted)}summary{cursor:pointer;color:var(--text)}li{margin:8px 0}.sources{margin-top:40px;border-top:1px solid var(--line);padding-top:24px}
.sources ul{padding:0;list-style:none}.sources li{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;border-bottom:1px solid var(--line);padding:12px 0;font-size:12px}.sources em{color:var(--accent);font-style:normal}
footer{color:var(--muted);font-size:12px;margin-top:30px}a{color:var(--accent)}.empty{padding:40px 20px;border:1px dashed var(--line);margin-top:20px;border-radius:12px;color:var(--muted)}[hidden]{display:none!important}
@media(max-width:950px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){main{padding:20px 16px 40px}.grid{grid-template-columns:1fr}.stats{gap:8px}.stat{padding:12px}.stat strong{font-size:20px}}
</style></head><body><main><div class="brand">PROUDMOORE / MARKET WATCH</div><header>
<h1>A shorter auction session.<br>A clearer decision.</h1><p class="intro">A small research watchlist for Retail on Proudmoore-US. Review the evidence, verify prices in game, and keep your playtime.</p></header>
""" + f"""<div class="notice" role="status"><strong>{mode}</strong><span id="health">Status: {escape(report['status'])}.</span>
<p>No purchases recommended yet. Listing depth, exact variants, your inventory, and trading results still need validation. Projected profits assume a successful sale.</p>{error}</div>
<div class="stats"><div class="stat"><small>Trading capital</small><strong>{config['budget_gold']:,}g</strong></div>
<div class="stat"><small>Cash held back</small><strong>{config['reserve_gold']:,}g</strong></div>
<div class="stat"><small>Daily session cap</small><strong>15 min</strong></div></div>
<section><div class="section-head"><h2>Research watchlist</h2><div role="group" aria-label="Market filter">
<button aria-pressed="true" data-filter="all">All</button> <button aria-pressed="false" data-filter="commodities">US commodities</button>
<button aria-pressed="false" data-filter="realm">Proudmoore items</button></div></div>
<p class="muted">Showing up to {config['max_watchlist_items']} candidates, ranked by projected profit per unit. Regional demand is not your personal chance of a sale.</p>
{empty}<div class="grid">{''.join(cards)}</div><p id="filter-empty" class="muted" hidden>No candidates in this market.</p></section>
<section class="sources"><h2>Source health</h2><ul>{source_html}</ul>
<p class="muted">Report generated {escape(report['generated_at'])}. Prices are snapshots, not live quotes. The page checks source expiry while open.</p></section>
<footer>Research ceiling includes a {config['auction_cut_bps']/100:g}% AH cut, {config['resale_markdown_bps']/100:g}% resale markdown, and {config['lost_deposit_allowance_gold']}g lost-deposit allowance per unit.
These are configurable planning assumptions, not verified listing fees. No token price is connected yet.<br>
Data: <a href="https://tradeskillmaster.com/public-data">TradeSkillMaster</a>. Unofficial fan project; no automated game actions.</footer></main>
""" + """<script>
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-filter]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
  let visible=0;document.querySelectorAll('[data-scope]').forEach(card=>{
    card.hidden=button.dataset.filter!=='all'&&card.dataset.scope!==button.dataset.filter;if(!card.hidden)visible++;
  });document.getElementById('filter-empty').hidden=visible>0;
}));
function freshness(){let stale=false;document.querySelectorAll('[data-expiry]').forEach(source=>{
  if(Date.now()>Date.parse(source.dataset.expiry)){source.querySelector('em').textContent='STALE';stale=true;}
});if(stale)document.getElementById('health').textContent='STALE DATA · Refresh after a successful cloud scan.';}
freshness();setInterval(freshness,60000);
</script></body></html>"""
