# Validation record

## Filter hierarchy and column alignment - October 29, 2026

The latest interface places all five filters inside a single dropdown. The option panel sits below the button with a visible gap; selection, Escape, and clicking outside close it. Client names and statuses use consistent desktop columns, status dots were removed, summary numbers are larger than labels, and meeting dates use readable month names without changing timezone handling.

JavaScript syntax and browser checks passed with Microsoft Edge. Checks cover all five filters, keyboard selection, reopening and closing the dropdown, separation of button/panel borders, alignment across all 29 rows, source details, candidate links, safe text rendering, errors, and 390px/320px layouts. Desktop, open-dropdown, and mobile screenshots were reviewed.

## Interface refinement — October 29, 2026

The filter dropdown was replaced with native radio filters, and the page was refined into one aligned meeting list. JavaScript syntax and browser checks passed using Microsoft Edge. Checks cover all five filters, arrow-key selection, search, source comparisons, candidate navigation, error handling, and widths of 390px and 320px. Desktop, mobile, and focused-filter screenshots were inspected; filter borders and focus outlines are complete.

## Readability refactor ? October 28, 2026

Validated locally on Windows with Python 3.12.10, Node 24.21.0, and Playwright 1.64.1 using Microsoft Edge headlessly.

- All 46 Python tests passed.
- The complete reconciled output equals the saved output from before the refactor: meeting IDs, field choices, observations, matching reasons, review links, and totals.
- JavaScript syntax and browser interaction checks passed. The browser checks include readable 17px body/control text, one summary status per meeting, collapsed source comparisons, search, filters, raw records, candidate navigation, safe rendering of source text, and server errors.
- The page fits widths of 390px and 320px, including an expanded source table. Desktop and mobile screenshots were inspected.

The refactor changes names and structure, while retaining the reconciliation policy and API response format.

## Earlier package validation

The following records describe the earlier packaged revision, not checks repeated during the readability refactor.

| Check | Executed result |
|---|---|
| Python 3.12.14, `python3 -m unittest discover -s tests -v` | **46 tests passed** |
| `python3 -m compileall -q app.py event_sync` | Passed |
| Node 24.22.1, `node --check static/app.js` | Passed |
| `node --check tests/browser-smoke.cjs` | Passed |
| Playwright 1.51.1 / Chromium headless shell 134 | **Browser smoke test passed** |
| Original inputs vs packaged files | Byte-for-byte equality verified |
| ZIP | Integrity, clean extraction, tests and actual CLI/API startup verified before delivery |

The Python tests cover normalization, source IDs, date/time construction, precise time boundaries, timezone-awareness mismatch, missing/invalid values, ambiguity, possible/exact duplicates, cancellation, attendee validation, recurring occurrences, every original row, deterministic membership/IDs, source-only entries, source-ID search, API filters, detail endpoints, static assets, bad requests and startup failures.

Browser checks cover 29 displayed entries, expanded details and provenance, 13 conflict entries, search/empty state, original raw records, candidate navigation that clears filters and opens the target, text-only rendering of a hostile `<img onerror>` string, mobile width with collapsed/expanded meetings, and API error handling without stale results. No page JavaScript errors were reported. The source-local time labels and responsive layout were also visually inspected.

## Re-run browser checks (optional development dependencies)

The running app and Python tests need no Node packages. For the optional browser test:

```sh
npm install --no-save --package-lock=false playwright@1.51.1
npx playwright install chromium --only-shell
python3 tests/run_browser.py
```

On a minimal Linux machine, `npx playwright install --with-deps chromium --only-shell` can install the required system libraries. The Python runner starts a temporary app server on an available port, runs the smoke test, then stops the server. Alternatively, start the app yourself and run `node tests/browser-smoke.cjs`; `BASE_URL` overrides port 8000. Set `BROWSER_CHANNEL=msedge` to use an installed Microsoft Edge browser instead of downloaded Chromium.

Initial browser-download attempts failed in the authoring environment. A pinned Playwright version and its alternate download mirror succeeded; the final browser checks above were then actually executed. There is no browser-download dependency at application runtime.

## Not executed during the earlier package validation

Docker build/runtime, remote GitHub Actions, Codespaces provisioning, large-scale performance testing, and screen-reader accessibility testing. Their configurations or standard-platform support do not imply those environments were verified. Automated pair expectations reflect documented policy, not external ground-truth labels.
