# Deployment status — 31 October 2026

- Public repository (explicit owner choice): https://github.com/rclee/proudmoore-market-scanner
- Local scanner: working against all three live feeds.
- Local phone-readable report: `output/live/index.html`.
- Initial validation: `docs/DATA_VALIDATION.md`.
- Checks: 18 behavioral tests, clean Python type check, phone/desktop browser checks, and local integration check of the exact cloud state scripts.
- Hourly schedule: configured at minute 47 UTC; manual cloud scan and durable history restore **verified successfully**.

The first hosted workflow was blocked before any steps ran:

https://github.com/rclee/proudmoore-market-scanner/actions/runs/41218532060

GitHub reported that recent account payments failed or a spending limit must be increased. The account owner explicitly selected public repository visibility. No billing settings were changed.

The first public cloud run completed successfully and restored the history seeded from the local scan:

https://github.com/rclee/proudmoore-market-scanner/actions/runs/41218753221

The downloaded initial cloud report confirmed 18 watchlist candidates, zero actionable buys, and 18 retained price observations without duplicate scans. Counts change as new snapshots arrive. Latest results are under Actions → Market scan.

## Daily simplification delivered

- Live owner-private phone page: https://proudmoore-daily-gold.airofcozy.chatgpt.site
- New public report branch: `scanner-report`, containing generated JSON and HTML only.
- Successful collector/report-publication run: https://github.com/rclee/proudmoore-market-scanner/actions/runs/41219599568
- The page fetched the actual cloud feed successfully in browser verification. It defaults to SKIP and keeps resale research behind an optional section.
- Vendor-profit checker: exact integer-copper arithmetic, full lot cost, 20% buffer, 10g minimum profit, 4,000g lot limit, entered remaining session budget, input-edit reset, and 60-second confirmation expiry.
- Verification: 20 Python tests and clean type check, 8 JavaScript tests, phone/desktop browser checks, and both review axes without material findings.
- The TSM formula follows official documentation but has not been exercised in a live WoW client. That limitation appears beside the formula.
- No verified vendor opportunities, executed trades, or token-funding results have been established. The public feeds do not contain exact vendor values.

No subscription or Blizzard credentials are needed for this first milestone. No trades have been made or recommended.
