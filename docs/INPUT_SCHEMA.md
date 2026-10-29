# Source adapters

The original assessment files in `data/` are the application's default inputs. They are not rewritten during normalization. Both roots must be JSON arrays. Non-object rows survive with validation issues; file-level JSON/root errors fail startup.

| Canonical field | CRM input | Calendar input |
|---|---|---|
| source_id | crm_id | event_id |
| title | subject | title |
| start | meeting_date + meeting_time | start_time |
| end | absent | end_time |
| date | meeting_date | derived from normalized start |
| client | client_name | absent |
| company | client_company | absent |
| owner | relationship_owner | absent |
| organizer | absent | organizer |
| attendees | absent | attendees |
| location | location | location |
| meeting_type | meeting_type | Virtual derived only from explicit platform in location |
| status | status | status |
| notes | notes | absent |
| description | absent | description |
| is_recurring | absent | is_recurring |
| recurrence | absent | optional recurrence/recurrence_rule |

`created_at` and all unknown keys remain in raw records. Created timestamps do not establish update freshness and are not used to select a duplicate's “latest” version.

Generic aliases remain supported for isolated tests/alternative schemas: title/subject/summary/meeting_title; start/start_time/meeting_date/date; end/end_time; client/client_name; company/client_company; owner/relationship_owner; attendees/participants; location/meeting_location. The first present non-null alias wins. Empty or invalid earlier aliases are not silently replaced by later ones. Original source IDs fall back to `id` for alternate schemas.

Attendees accept email strings or objects with `email`. Recurrence accepts a string or string list. `is_recurring` must be a boolean. Text fields must be strings. Start/end accept ISO datetimes or an object containing `dateTime`. CRM dates support `YYYY-MM-DD` and the narrow legacy `MM-DD/YYYY` format, with a review warning for the latter. A separate CRM time must be `HH:MM` or `HH:MM:SS`.

Timezone-free times stay floating local times. Aware times become UTC. There is no default timezone, city lookup, DST offset guess, all-day expansion, or fuzzy date repair. Invalid emails such as `raj.patel[at]atlasvc.com` and placeholders such as `external-guests` are preserved in raw input rather than guessed. An end time before/equal to start, or using a different timezone basis, is omitted from normalized output with an issue.

Every normalized field includes its source key(s), original value, normalized value, source name, source ID and row. Derived values explicitly identify the derivation. Record normalization notes document shared-clock assumptions; issues identify unusable/legacy values.
