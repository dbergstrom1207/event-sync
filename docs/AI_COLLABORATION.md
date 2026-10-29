# AI collaboration record

The assessment explicitly encourages transparent AI assistance. OpenAI Codex assisted with the design, implementation, tests, documentation, and packaging. The running application itself uses no model, network AI service, or API key.

## Development sequence and corrections

1. The first request contained the brief without the JSON attachments. A runnable baseline was created using clearly labeled synthetic fixtures.
2. The user subsequently supplied the original CRM/calendar files and problem statement and requested a completed GitHub-ready project.
3. The actual schemas were inspected. The earlier assumptions were corrected: CRM date/time are separate, source IDs are `crm_id`/`event_id`, titles differ, attendee data is absent in CRM, and most times lack timezone information.
4. Reconciliation was adapted to the real records using explicit client/owner email-name evidence and title/description topics, with a review graph for uncertain candidates.
5. Pinnacle near-duplicates were preserved; UTC/local disagreement and missing/two-hour-shifted times became review candidates. Cancellation, recurring flags, invalid emails and the legacy date spelling gained regression tests.
6. The application default files were replaced with the supplied originals. Synthetic fixtures were moved to `tests/fixtures/` and are not loaded by the application.
7. Documentation, GitHub Actions, Codespaces configuration, and an optional browser smoke script were updated for the final implementation.

## Alternatives considered

- Assigning America/New_York or a fixed UTC offset: rejected because the source timezone is unspecified and daylight saving makes a guessed fixed offset especially misleading.
- Greedy matching or always selecting the closest time: rejected because CRM-1005 has competing Pinnacle entries.
- Keeping only the newest `created_at`: rejected because creation time does not establish edit/version lineage.
- Requiring exact titles: rejected for actual data because many obvious candidate meetings have renamed titles.
- Automatically correcting malformed email addresses: rejected because the true intended address cannot be established from the string alone.
- Expanding recurrence: rejected because a boolean supplies no recurrence rule and concrete occurrences already exist.
- Database/framework build system: deferred for a small, local, read-only assessment to keep setup simple and decisions inspectable.

## Verification and ownership

Automated tests validate documented outcomes, not external ground truth. Human reviewers should evaluate identity and timezone assumptions and understand review-only cases. The candidate's personal review time was not observed and must be reported honestly. Do not describe this code as independently written without assistance. See `VALIDATION.md` for what actually ran and what could not be verified.

## Readability revision

At the user's request, the interface was simplified to a readable meeting list with 17px text and details opened on demand. The matching and server code was refactored into named steps, and the README was shortened to explain the flow. The full supplied-data output was compared with the pre-refactor result, and Python and browser checks were rerun. Project preferences are recorded in `AGENTS.md`.
