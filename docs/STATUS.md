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

The downloaded cloud report confirmed 18 watchlist candidates, zero actionable buys, and 18 retained price observations without duplicate scans. Latest results are under Actions → Market scan. A direct hosted dashboard is still a next milestone; currently download and extract the report artifact to open its HTML.

No subscription or Blizzard credentials are needed for this first milestone. No trades have been made or recommended.
