# Decision log

| Decision | Reason | Tradeoff |
|---|---|---|
| Read original JSON files at startup | Exact supplied interfaces, no invented remote API | Restart needed after source changes |
| Standard-library Python and vanilla JS | One command, no runtime package installation | Bundled server is local-use hosting |
| Preserve timezone-free times | No timezone supplied by assessment | Cannot auto-merge local/UTC candidates |
| Narrow legacy date parser | `03-15/2025` is recognizable without locale guessing | Warning retained; arbitrary formats rejected |
| Client/owner names compared with whole email local parts | Supplied sources have no common ID or CRM email | Heuristic identity, not directory verification |
| Description topic overlap plus owner evidence | Supports internal renamed meetings such as LPAC/QBR | Broad topics can still cause false candidates |
| 30-minute automatic / 4-hour review windows | Small discrepancies vs possible reschedules | Thresholds require business calibration |
| Stricter 10-minute generic equal-title fallback | Shared attendee can be weak identity evidence | May miss legitimate alternate-schema matches |
| Mutually unique candidates only | Prevent order-dependent arbitrary merges | More review entries than a greedy algorithm |
| Preserve CAL-A5/CAL-A6 as possible duplicates | Different attendees, titles, and times; no version lineage | No unsupported “latest version” selection |
| Cancellation from either source wins | Avoid presenting a cancelled meeting as confirmed | Stale cancellations require human resolution |
| Owner and organizer separate | Relationship responsibility is not invitation ownership | More fields, clearer semantics |
| Show raw and normalized values | Full auditability of conflicts and malformed data | Payload contains source contact information |
| No recurrence expansion | Files contain concrete occurrences and only a boolean | Full recurrence rules need future modeling |
| Content-derived snapshot IDs | Deterministic under reordering | IDs change with content or merge membership |
