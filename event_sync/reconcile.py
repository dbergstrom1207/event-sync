"""Normalize source records, match meetings, and keep the reasons for each decision."""

from datetime import datetime, date, timezone
from hashlib import sha256
import json
import re

FIELDS = (
    "title",
    "start",
    "end",
    "date",
    "client",
    "company",
    "owner",
    "organizer",
    "attendees",
    "location",
    "meeting_type",
    "status",
    "notes",
    "description",
    "is_recurring",
    "recurrence",
)
ALIASES = {
    "title": ("title", "subject", "summary", "meeting_title"),
    "start": ("start", "start_time", "meeting_date", "date"),
    "end": ("end", "end_time"),
    "date": ("meeting_date", "date"),
    "client": ("client", "client_name"),
    "company": ("company", "client_company"),
    "owner": ("owner", "relationship_owner"),
    "organizer": ("organizer",),
    "attendees": ("attendees", "participants"),
    "location": ("location", "meeting_location"),
    "meeting_type": ("meeting_type",),
    "status": ("status",),
    "notes": ("notes",),
    "description": ("description",),
    "is_recurring": ("is_recurring",),
    "recurrence": ("recurrence", "recurrence_rule"),
}
CRM_FIELDS = {"client", "company", "owner", "notes", "status", "meeting_type"}
PREFERRED = {field: "crm" if field in CRM_FIELDS else "calendar" for field in FIELDS}
AUTO_WINDOW = 30 * 60
REVIEW_WINDOW = 4 * 60 * 60


def serialize_record(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def comparison_value(value):
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value.strip().casefold())
    return serialize_record(value)


def simplify_name(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def name_matches_email(name, emails):
    # Full name must equal the whole email local part after punctuation removal.
    # No fuzzy surname or initials-only matching; this remains a heuristic.
    if not name or len(name.split()) < 2:
        return False
    full_name = simplify_name(name)
    return any(full_name == simplify_name(email.split("@")[0]) for email in emails)


def title_words(value):
    return set(re.findall(r"[a-z0-9]+", (value or "").casefold())) - {
        "the",
        "and",
        "with",
        "for",
        "of",
        "a",
        "in",
        "on",
        "to",
        "meeting",
        "session",
    }


def normalize_timestamp(value):
    if isinstance(value, dict):
        value = value.get("dateTime")
    if not isinstance(value, str) or "T" not in value:
        raise ValueError("expected ISO 8601 datetime")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # No timezone is invented. Floating local times stay floating.
    if timestamp.tzinfo is None:
        return timestamp.isoformat()
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_date(value):
    if not isinstance(value, str):
        raise ValueError("expected date string")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value).isoformat(), False
    if re.fullmatch(r"\d{2}-\d{2}/\d{4}", value):
        return datetime.strptime(value, "%m-%d/%Y").date().isoformat(), True
    raise ValueError("expected YYYY-MM-DD or explicit MM-DD/YYYY legacy format")


def normalize_record(source, raw, index):
    issues = []
    normalization_notes = []
    values = {}
    field_sources = {}
    original_values = {}
    raw_record = raw if isinstance(raw, dict) else {}
    if not isinstance(raw, dict):
        issues.append("Record is not an object; preserved for review")
    for field in FIELDS:
        source_field = next(
            (
                candidate_field
                for candidate_field in ALIASES[field]
                if raw_record.get(candidate_field) is not None
            ),
            None,
        )
        value = raw_record.get(source_field) if source_field else None
        field_sources[field], original_values[field] = source_field, value
        try:
            if value is None or value == "" or value == []:
                value = None
            elif (
                field == "start"
                and source == "crm"
                and source_field == "meeting_date"
                and "T" not in str(value)
            ):
                meeting_date, used_legacy_format = normalize_date(value)
                field_sources[field] = "meeting_date + meeting_time"
                original_values[field] = {
                    "meeting_date": value,
                    "meeting_time": raw_record.get("meeting_time"),
                }
                if used_legacy_format:
                    issues.append(
                        "Legacy meeting_date normalized from MM-DD/YYYY; verify interpretation"
                    )
                meeting_time = raw_record.get("meeting_time")
                if meeting_time is None or meeting_time == "":
                    raise ValueError(
                        "meeting_time missing; date retained, automatic matching disabled"
                    )
                if not isinstance(meeting_time, str) or not re.fullmatch(
                    r"\d{2}:\d{2}(:\d{2})?", meeting_time
                ):
                    raise ValueError("meeting_time must be HH:MM or HH:MM:SS")
                value = normalize_timestamp(meeting_date + "T" + meeting_time)
            elif field in ("start", "end"):
                value = normalize_timestamp(value)
            elif field == "date":
                # An alternate full timestamp is handled by start, not by this date field.
                if isinstance(value, str) and "T" in value:
                    value = None
                else:
                    value, _ = normalize_date(value)
            elif field == "attendees":
                if not isinstance(value, list):
                    raise ValueError("expected array of emails or objects with email")
                emails = []
                for item in value:
                    email = item.get("email") if isinstance(item, dict) else item
                    if not isinstance(email, str) or not re.fullmatch(
                        r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()
                    ):
                        issues.append(
                            "attendees: invalid entry omitted from normalized list; original preserved"
                        )
                    else:
                        emails.append(email.strip().lower())
                value = sorted(set(emails)) or None
            elif field == "is_recurring":
                if not isinstance(value, bool):
                    raise ValueError("expected boolean")
            elif field == "recurrence":
                if not isinstance(value, (str, list)) or (
                    isinstance(value, list)
                    and not all(isinstance(item, str) for item in value)
                ):
                    raise ValueError("expected string or array of strings")
                value = (
                    [value.strip()] if isinstance(value, str) else sorted(set(value))
                )
            else:
                if not isinstance(value, str):
                    raise ValueError("expected string")
                value = value.strip() or None
                if field == "status" and value:
                    value = comparison_value(value)
                    if value == "canceled":
                        value = "cancelled"
        except (ValueError, TypeError, OverflowError) as exc:
            issues.append(f"{field}: {exc}")
            value = None
        values[field] = value
    if values["start"] and not values["date"]:
        values["date"] = values["start"][:10]
        field_sources["date"], original_values["date"] = (
            field_sources["start"],
            original_values["start"],
        )
    for field in ("title", "start"):
        if not values[field]:
            issues.append(f"Missing usable {field}; automatic matching disabled")
    time_basis = "unknown"
    if values["start"]:
        time_basis = "UTC" if values["start"].endswith("Z") else "local-unspecified"
        if time_basis == "local-unspecified":
            normalization_notes.append(
                "Timezone absent: displayed as source-local time; compared only with other unspecified local times under a shared-clock assumption"
            )
    if values["end"] and values["start"]:
        start, end = (
            datetime.fromisoformat(values[field]) for field in ("start", "end")
        )
        if (start.tzinfo is None) != (end.tzinfo is None):
            issues.append("start/end timezone basis differs; normalized end omitted")
            values["end"] = None
        elif end <= start:
            issues.append("end must be after start; normalized end omitted")
            values["end"] = None
    # Virtual modality can be derived from an explicit platform, but physical presence is not guessed.
    if (
        source == "calendar"
        and not values["meeting_type"]
        and re.search(
            r"\b(zoom|teams|virtual|google meet)\b", values["location"] or "", re.I
        )
    ):
        values["meeting_type"] = "Virtual"
        field_sources["meeting_type"], original_values["meeting_type"] = (
            "location (derived modality)",
            raw_record.get("location"),
        )
        normalization_notes.append(
            "meeting_type derived as Virtual from an explicit video platform in location"
        )
    record_hash = sha256((source + serialize_record(raw)).encode()).hexdigest()[:20]
    return {
        "ref": f"{source}:{record_hash}",
        "source": source,
        "source_id": raw_record.get(
            "crm_id" if source == "crm" else "event_id", raw_record.get("id")
        ),
        "row": index + 1,
        "raw": raw,
        "values": values,
        "origins": field_sources,
        "originals": original_values,
        "issues": issues,
        "normalization_notes": normalization_notes,
        "time_basis": time_basis,
    }


def duplicate_signature(record):
    values = record["values"]
    if record["issues"] or not all(
        values[field] for field in ("title", "start", "attendees")
    ):
        return record["ref"]
    return serialize_record(
        {
            field: (
                comparison_value(values[field])
                if isinstance(values[field], str)
                else values[field]
            )
            for field in FIELDS
        }
    )


def compare_start_times(first, second):
    if not first["start"] or not second["start"]:
        return None, "Missing start time"

    first_start = datetime.fromisoformat(first["start"])
    second_start = datetime.fromisoformat(second["start"])
    if (first_start.tzinfo is None) != (second_start.tzinfo is None):
        return (
            None,
            "Timezone mismatch: UTC and unspecified local time cannot be compared safely",
        )

    difference = abs((first_start - second_start).total_seconds())
    if first_start.tzinfo:
        return difference, "UTC instants"
    return difference, "Shared unspecified local clock assumption"


def find_match_reason(first_record, second_record):
    """Return the evidence for a possible CRM/calendar pair, or None."""
    if first_record["source"] == "calendar":
        first_record, second_record = second_record, first_record
    crm = first_record["values"]
    calendar = second_record["values"]
    if not crm["title"] or not calendar["title"]:
        return None

    same_client = bool(
        crm["client"]
        and calendar["client"]
        and comparison_value(crm["client"]) == comparison_value(calendar["client"])
    )
    if crm["client"] and calendar["client"] and not same_client:
        return None

    shared_emails = sorted(
        set(crm["attendees"] or []) & set(calendar["attendees"] or [])
    )
    calendar_people = list(calendar["attendees"] or [])
    if calendar["organizer"]:
        calendar_people.append(calendar["organizer"])
    client_email_match = name_matches_email(crm["client"], calendar["attendees"] or [])
    owner_present = name_matches_email(crm["owner"], calendar_people)
    shared_topics = sorted(
        title_words(crm["title"])
        & title_words((calendar["title"] or "") + " " + (calendar["description"] or ""))
    )
    same_title = comparison_value(crm["title"]) == comparison_value(calendar["title"])

    automatic_limit = AUTO_WINDOW
    if client_email_match and owner_present:
        rule = "Client full name matches attendee email; relationship owner is organizer/attendee"
    elif owner_present and len(shared_topics) >= 2:
        rule = "Relationship owner is organizer/attendee and at least two title topics occur in calendar title/description"
    elif same_title and (same_client or shared_emails):
        rule = "Equal normalized title and same client or shared email"
        automatic_limit = 10 * 60
    else:
        return None

    difference, time_basis = compare_start_times(crm, calendar)
    if difference is None:
        if not crm["date"] or crm["date"] != calendar["date"]:
            return None
    elif difference > REVIEW_WINDOW:
        return None

    automatic = difference is not None and difference <= automatic_limit
    review_reason = None
    if difference is None:
        review_reason = time_basis
    elif not automatic:
        review_reason = "Time difference exceeds automatic window"

    return {
        "rule": rule,
        "automatic": automatic,
        "start_delta_seconds": difference,
        "time_basis": time_basis,
        "same_client": same_client,
        "shared_emails": shared_emails,
        "client_email_match": client_email_match,
        "owner_present": owner_present,
        "shared_topics": shared_topics,
        "review_reason": review_reason,
    }


def find_duplicate_reason(first_record, second_record):
    if first_record["source"] != second_record["source"]:
        return None
    first = first_record["values"]
    second = second_record["values"]
    difference, _ = compare_start_times(first, second)
    if difference is None or difference > AUTO_WINDOW:
        return None

    organizer = first["organizer"]
    if not organizer or organizer != second["organizer"]:
        return None
    shared_attendees = set(first["attendees"] or []) & set(second["attendees"] or [])
    organizer_domain = organizer.split("@")[-1]
    external_attendees = {
        email for email in shared_attendees if email.split("@")[-1] != organizer_domain
    }
    shared_topics = title_words(first["title"]) & title_words(second["title"])
    if not external_attendees or not shared_topics:
        return None
    return {
        "kind": "possible_duplicate",
        "rule": "Same organizer, shared external attendee and title topic, starts within 30 minutes",
        "start_delta_seconds": difference,
        "shared_emails": sorted(external_attendees),
    }


def select_field_value(field, records):
    """Choose one source value while retaining every original and the selection rule."""
    observations = []
    for record in records:
        observations.append(
            {
                "source": record["source"],
                "source_id": record["source_id"],
                "record_ref": record["ref"],
                "row": record["row"],
                "source_field": record["origins"][field],
                "raw_value": record["originals"][field],
                "value": record["values"][field],
            }
        )

    usable = [
        observation for observation in observations if observation["value"] is not None
    ]
    selected = usable[0] if usable else None
    for observation in usable:
        if observation["source"] == PREFERRED[field]:
            selected = observation
            break
    policy = f"Prefer {PREFERRED[field]}; fall back to other source"

    if field == "status":
        for observation in usable:
            if observation["value"] == "cancelled":
                selected = observation
                policy = "Cancellation from either source takes precedence; keep disagreement visible"
                break

    distinct_values = {comparison_value(observation["value"]) for observation in usable}
    return {
        "value": selected["value"] if selected else None,
        "selected_source": selected["source"] if selected else None,
        "selected_record_ref": selected["record_ref"] if selected else None,
        "policy": policy,
        "conflict": len(distinct_values) > 1,
        "observations": observations,
    }


def build_meeting(groups, match_reason=None, candidates=None):
    records = [record for group in groups for record in group]
    records.sort(key=lambda record: (record["source"], record["ref"], record["row"]))
    fields = {field: select_field_value(field, records) for field in FIELDS}
    record_refs = sorted({record["ref"] for record in records})
    candidates = candidates or []
    return {
        "id": sha256("|".join(record_refs).encode()).hexdigest()[:20],
        "fields": fields,
        "sources": sorted({record["source"] for record in records}),
        "records": records,
        "match": match_reason,
        "candidate_refs": sorted({candidate["record_ref"] for candidate in candidates}),
        "candidates": candidates,
        "duplicate_count": sum(len(group) - 1 for group in groups),
        "has_conflicts": any(field["conflict"] for field in fields.values()),
        "needs_review": bool(candidates)
        or fields["status"]["conflict"]
        or any(record["issues"] for record in records),
    }


def group_duplicate_records(crm_records, calendar_records):
    """Normalize records and group only exact duplicates within each source."""
    groups = []
    for source, rows in (("crm", crm_records), ("calendar", calendar_records)):
        if not isinstance(rows, list):
            raise ValueError(f"{source}: root must be a JSON array")
        duplicates = {}
        for index, raw_record in enumerate(rows):
            record = normalize_record(source, raw_record, index)
            signature = duplicate_signature(record)
            duplicates.setdefault(signature, []).append(record)
        for group in duplicates.values():
            group.sort(key=lambda record: (record["ref"], record["row"]))
            groups.append(group)
    groups.sort(key=lambda group: group[0]["ref"])
    return groups


def find_candidates(groups):
    """Keep all possible links so ambiguous records cannot be merged greedily."""
    matches = {index: {} for index in range(len(groups))}
    duplicates = {index: {} for index in range(len(groups))}
    for first_index, first_group in enumerate(groups):
        for second_index in range(first_index + 1, len(groups)):
            first = first_group[0]
            second = groups[second_index][0]
            if first["source"] != second["source"]:
                reason = find_match_reason(first, second)
                if reason:
                    matches[first_index][second_index] = reason
                    matches[second_index][first_index] = reason
            else:
                reason = find_duplicate_reason(first, second)
                if reason:
                    duplicates[first_index][second_index] = reason
                    duplicates[second_index][first_index] = reason
    return matches, duplicates


def collect_review_candidates(group_index, groups, matches, duplicates):
    candidates = []
    for target_index, reason in matches[group_index].items():
        record = groups[target_index][0]
        candidates.append(
            {
                "record_ref": record["ref"],
                "source_id": record["source_id"],
                "kind": "cross_source",
                **reason,
            }
        )
    for target_index, reason in duplicates[group_index].items():
        record = groups[target_index][0]
        candidates.append(
            {
                "record_ref": record["ref"],
                "source_id": record["source_id"],
                **reason,
            }
        )
    return candidates


def merge_unambiguous_matches(groups, matches, duplicates):
    meetings = []
    used_groups = set()
    for group_index, group in enumerate(groups):
        if group_index in used_groups:
            continue

        possible_matches = matches[group_index]
        if len(possible_matches) == 1:
            other_index, reason = next(iter(possible_matches.items()))
            can_merge = (
                len(matches[other_index]) == 1
                and reason["automatic"]
                and not duplicates[group_index]
                and not duplicates[other_index]
            )
            if can_merge:
                meetings.append(build_meeting([group, groups[other_index]], reason))
                used_groups.update((group_index, other_index))
                continue

        candidates = collect_review_candidates(group_index, groups, matches, duplicates)
        meetings.append(build_meeting([group], candidates=candidates))
        used_groups.add(group_index)
    return meetings


def link_review_candidates(meetings):
    meeting_for_record = {}
    for meeting in meetings:
        for record in meeting["records"]:
            meeting_for_record[record["ref"]] = meeting["id"]
    for meeting in meetings:
        for candidate in meeting["candidates"]:
            candidate["meeting_id"] = meeting_for_record[candidate["record_ref"]]


def reconcile(crm, calendar):
    """Read top to bottom: normalize, find candidates, merge, link, and summarize."""
    groups = group_duplicate_records(crm, calendar)
    matches, duplicates = find_candidates(groups)
    meetings = merge_unambiguous_matches(groups, matches, duplicates)
    link_review_candidates(meetings)

    # Source-local dates and UTC times do not form a shared global timeline.
    meetings.sort(
        key=lambda meeting: (
            meeting["fields"]["date"]["value"] or "9999",
            meeting["fields"]["start"]["value"] or "9999",
            meeting["id"],
        )
    )
    return {
        "meetings": meetings,
        "summary": {
            "input_records": len(crm) + len(calendar),
            "meetings": len(meetings),
            "matched": sum(bool(meeting["match"]) for meeting in meetings),
            "conflicts": sum(meeting["has_conflicts"] for meeting in meetings),
            "review": sum(meeting["needs_review"] for meeting in meetings),
            "duplicates_collapsed": sum(
                meeting["duplicate_count"] for meeting in meetings
            ),
        },
    }
