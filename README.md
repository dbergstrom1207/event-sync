# Event Sync Service

Read CRM and calendar JSON files, find records for the same meeting, and explain which source supplied each value. The browser page lets you search meetings and inspect conflicts.

## Run locally

Requires **Python 3.11+**. The app uses Python's standard library; no packages, database, API keys, or frontend build are needed.

From this folder, run:

```sh
python app.py
```

On macOS/Linux, use `python3 app.py` if needed. On Windows, `py -3 app.py` also works when the Python launcher is installed. If a command is not recognized, reopen the terminal after installing Python or use the full path to `python.exe`.

Open **http://127.0.0.1:8000**. Keep the terminal open and press **Ctrl+C** to stop.

```sh
python app.py --port 8080
python app.py --data-dir /path/to/data
```

The default `data/` folder contains the supplied **20 CRM records and 22 calendar records**. A different data folder must contain `crm_events.json` and `calendar_events.json`. Files are read at startup, so restart after editing them. **Refresh view** fetches the existing snapshot.

## Use the page

1. Search by title, client, owner, or original source ID, such as `CRM-1002`.
2. Select **Needs review** or **Conflicting values** to narrow the list.
3. Open a meeting to read the matching decision and any review reasons.
4. Open **Compare source values** to see selected values and conflicts. **Why this value?** shows the source inputs and selection rule.
5. Open **Raw records and validation issues** for the original data.

Each meeting has one summary status. Cancellation takes priority, then review, conflicts, matched, and single source. A meeting can be both matched and in need of review; its full decision remains available when opened. The totals count these overlapping categories separately.

## Follow the code

Start with `reconcile()` in [event_sync/reconcile.py](event_sync/reconcile.py). It calls these steps in order:

| Function | Responsibility |
|---|---|
| `group_duplicate_records` | Normalize each source row and group exact duplicates |
| `find_candidates` | Find possible cross-source matches and same-source duplicates |
| `merge_unambiguous_matches` | Combine only a unique, eligible pair |
| `link_review_candidates` | Connect unresolved candidates to the meetings shown in the page |

`normalize_record` handles field names, dates, emails, and validation issues. `find_match_reason` explains why two records may refer to the same meeting. `select_field_value` chooses the preferred source and records conflicts.

[event_sync/server.py](event_sync/server.py) loads the files and handles HTTP requests. [static/app.js](static/app.js) fetches meetings with `loadMeetings` and builds their summaries and details. [static/styles.css](static/styles.css) contains the basic readable layout. [AGENTS.md](AGENTS.md) records the project's preference for simple presentation and clear logic.

## Matching rules

- Identity evidence comes from a client's full name matching an attendee email, with the relationship owner also present; or from the owner's presence and at least two shared title topics. An equal title with a shared attendee or client is a fallback. Different explicitly supplied clients block a match.
- Strong identity candidates within **30 minutes** can match automatically. The equal-title fallback uses **10 minutes**. Differences up to **4 hours** can become review candidates.
- Both records must have exactly one candidate, and neither may have a possible same-source duplicate. Competing records stay separate.
- UTC timestamps compare as instants. Times without a timezone remain local and use a documented shared-clock assumption. Local and UTC times are never assumed equivalent. Missing times are not replaced with midnight.
- Exact duplicates are grouped and all original rows retained. Similar records stay separate for review. Recurring events are not expanded.

These are explicit assumptions for the supplied data, not verified identity rules. See [the decision log](docs/DECISIONS.md) and [input schema](docs/INPUT_SCHEMA.md) for details.

## Choosing source values

| Data | Preferred source |
|---|---|
| Client, company, relationship owner, notes, status, meeting type | CRM |
| Title, dates/times, organizer, attendees, location, description, recurrence | Calendar |
| Cancellation | Either source; cancellation overrides other statuses |

If the preferred value is missing or invalid, use the other source. Differing usable values produce a conflict. Original values, normalized values, source IDs, and the selection rule remain available. Unknown timezones and malformed input stay visible as issues.

## Supplied-data results

| Result | Count |
|---|---:|
| Input records | 42 |
| Meetings | 29 |
| Cross-source matches | 13 |
| Meetings with conflicting values | 13 |
| Meetings needing review | 14 |
| Exact duplicates collapsed | 0 |

For example, `CRM-1002` and `CAL-A2` match despite different titles. `CRM-1005`, `CAL-A5`, and `CAL-A6` remain separate because there are competing candidates. `CRM-1009` keeps the cancellation even though the calendar says confirmed.

See [the complete decision review](docs/RECONCILIATION_RESULTS.md) for all pairings and retained entries. These counts describe this policy, not employer-provided ground truth.

## API

| GET route | Response |
|---|---|
| `/api/health` | Readiness and snapshot load time |
| `/api/meetings` | Meetings, global totals, and filtered count |
| `/api/meetings?q=CRM-1002&filter=conflicts` | Search and filter results |
| `/api/meetings/{id}` | One meeting with source values and evidence |

Filters: `all`, `review`, `conflicts`, `crm`, `calendar`. Unknown or repeated list parameters return 400. Missing resources return 404. Source filters include combined meetings containing that source.

## Checks and limits

```sh
python -m unittest discover -s tests -v
```

The 46 Python tests cover matching rules, edge cases, supplied data, and API behavior. Optional browser-check instructions and observed results are in [VALIDATION.md](docs/VALIDATION.md).

This is a local, read-only service. It does not authenticate users, save review decisions, poll external systems, or write changes back. Matching compares record pairs and is intended for small datasets. IDs are stable when unchanged records are reordered, but can change when content or group membership changes.

The repository includes optional Docker, GitHub Actions, and Codespaces configuration. GitHub Pages cannot run this Python backend. To use Codespaces, run `python app.py --host 0.0.0.0` and open forwarded port 8000. For Docker, run `docker build -t event-sync .` then `docker run --rm -p 127.0.0.1:8000:8000 event-sync`.

## Development notes

Codex assisted with implementation, tests, documentation, and refactoring. The running app makes no AI calls. See [AI_COLLABORATION.md](docs/AI_COLLABORATION.md) and [TIME_SPENT.md](docs/TIME_SPENT.md). Record your own review time before submission. The original brief is in [ASSESSMENT.md](docs/ASSESSMENT.md).
