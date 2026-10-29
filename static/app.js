"use strict";

const searchInput = document.getElementById("search");
const filterControls = document.getElementById("filter");
const filterMenu = document.getElementById("filter-menu");
const filterToggle = document.getElementById("filter-toggle");
const filterLabel = document.getElementById("filter-label");
const refreshButton = document.getElementById("refresh");
const meetingList = document.getElementById("meetings");
const statusMessage = document.getElementById("status");
const meetingTotals = document.getElementById("stats");

const fieldLabels = {
  title: "Title",
  start: "Start",
  end: "End",
  date: "Date",
  client: "Client",
  company: "Company",
  owner: "Relationship owner",
  organizer: "Calendar organizer",
  attendees: "Attendees",
  location: "Location",
  meeting_type: "Meeting type",
  status: "Status",
  notes: "CRM notes",
  description: "Calendar description",
  is_recurring: "Recurring",
  recurrence: "Recurrence",
};

function createElement(tag, text, className) {
  const element = document.createElement(tag);
  // Source data is text, including titles that happen to contain HTML.
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function formatValue(value) {
  if (value == null) return "Not provided or invalid";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatMeetingTime(meeting) {
  const start = meeting.fields.start.value;
  if (!start) {
    const date = meeting.fields.date.value;
    return date ? `${date} (time not provided)` : "Date and time not provided";
  }
  // Keep the source clock unchanged; a missing timezone is not the browser's timezone.
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const [date, clock] = start.replace(/Z$/, "").split("T");
  const [year, month, day] = date.split("-");
  const readableDate = `${Number(day)} ${months[Number(month) - 1]} ${year}`;
  const time = `${readableDate}, ${clock.replace(/:00$/, "")}`;
  return start.endsWith("Z") ? `${time} UTC` : `${time} (timezone unspecified)`;
}

function getMeetingStatus(meeting) {
  if (meeting.fields.status.value === "cancelled") {
    return {
      text: meeting.needs_review ? "Cancelled / needs review" : "Cancelled",
      className: "cancelled",
    };
  }
  if (meeting.needs_review)
    return { text: "Needs review", className: "needs-review" };
  if (meeting.has_conflicts)
    return { text: "Conflicting values", className: "needs-review" };
  if (meeting.match) return { text: "Matched", className: "matched" };
  return { text: "Single source", className: "" };
}

function createMeetingSummary(meeting) {
  const summary = createElement("summary");
  const title = createElement("div", undefined, "meeting-title");
  title.append(
    createElement("h2", meeting.fields.title.value || "Untitled meeting"),
    createElement("p", formatMeetingTime(meeting), "meeting-info"),
  );
  const status = getMeetingStatus(meeting);
  summary.append(
    title,
    createElement(
      "p",
      `Client: ${meeting.fields.client.value || "Not provided"}`,
      "meeting-client",
    ),
    createElement("span", status.text, `meeting-status ${status.className}`),
  );
  return summary;
}

function explainMatch(meeting) {
  if (meeting.match) {
    const minutes = meeting.match.start_delta_seconds / 60;
    return `Matched: ${meeting.match.rule}. Start times differ by ${minutes} minutes. ${meeting.match.time_basis}.`;
  }
  if (meeting.candidates.length) {
    return "Kept separate. Possible matches or duplicates need review before these records can be combined.";
  }
  return "Kept as a separate meeting because no unique match was found in the other source.";
}

function createReviewReasons(meeting) {
  const reasons = new Set();
  if (meeting.fields.status.conflict)
    reasons.add("The sources disagree about the meeting status.");
  for (const record of meeting.records) {
    for (const issue of record.issues) {
      reasons.add(
        `${record.source_id || record.source.toUpperCase()}: ${issue}`,
      );
    }
  }
  const list = createElement("ul", undefined, "review-reasons");
  for (const reason of reasons) list.append(createElement("li", reason));
  return list;
}

async function openCandidateMeeting(meetingId) {
  let target = document.getElementById(`meeting-${meetingId}`);
  if (!target) {
    searchInput.value = "";
    filterControls.querySelector('input[value="all"]').checked = true;
    filterLabel.textContent = "All meetings";
    filterMenu.open = false;
    clearTimeout(searchTimer);
    await loadMeetings();
    target = document.getElementById(`meeting-${meetingId}`);
  }
  if (target) {
    target.open = true;
    target.scrollIntoView({ block: "start" });
    target.querySelector("summary").focus();
  }
}

function createCandidate(candidate) {
  const section = createElement("div", undefined, "candidate");
  const label =
    candidate.kind === "possible_duplicate"
      ? "Possible duplicate"
      : "Possible match";
  section.append(
    createElement(
      "strong",
      `${label}: ${candidate.source_id || candidate.record_ref}`,
    ),
    createElement("p", candidate.rule),
    createElement(
      "p",
      candidate.review_reason ||
        "More than one candidate or a possible duplicate prevents automatic matching.",
    ),
  );
  const button = createElement(
    "button",
    `Inspect ${candidate.source_id || "candidate"}`,
  );
  button.type = "button";
  button.addEventListener("click", () =>
    openCandidateMeeting(candidate.meeting_id),
  );
  section.append(button);
  return section;
}

function createSourceComparison(field) {
  const cell = createElement("td");
  cell.append(
    createElement(
      "p",
      field.selected_source
        ? field.selected_source.toUpperCase()
        : "No usable source",
    ),
  );
  const comparison = createElement("details", undefined, "observations");
  comparison.append(
    createElement("summary", "Why this value?"),
    createElement("p", field.policy),
  );
  for (const observation of field.observations) {
    comparison.append(
      createElement(
        "p",
        `${observation.source.toUpperCase()} / ${observation.source_id || "no ID"} / row ${observation.row} / ${observation.source_field || "field absent"}`,
      ),
      createElement("p", `Original: ${formatValue(observation.raw_value)}`),
      createElement("p", `Normalized: ${formatValue(observation.value)}`),
    );
  }
  cell.append(comparison);
  return cell;
}

function createFieldTable(meeting) {
  const section = createElement("details", undefined, "field-details");
  const conflicts = Object.values(meeting.fields).filter(
    (field) => field.conflict,
  ).length;
  const label = conflicts
    ? `Compare source values (${conflicts} conflicting fields)`
    : "Compare source values";
  section.append(createElement("summary", label));
  const scrollArea = createElement("div", undefined, "table-wrap");
  scrollArea.tabIndex = 0;
  scrollArea.setAttribute("role", "region");
  scrollArea.setAttribute(
    "aria-label",
    "Field comparison; scroll horizontally on smaller screens",
  );
  const table = createElement("table");
  const tableHead = createElement("thead");
  const headings = createElement("tr");
  for (const label of ["Field", "Selected value", "Source and explanation"]) {
    const heading = createElement("th", label);
    heading.scope = "col";
    headings.append(heading);
  }
  tableHead.append(headings);
  const tableBody = createElement("tbody");
  for (const [name, field] of Object.entries(meeting.fields)) {
    const row = createElement("tr");
    const heading = createElement("th", fieldLabels[name] || name);
    heading.scope = "row";
    if (field.conflict)
      heading.append(
        createElement("span", "Conflicting values", "conflict-label"),
      );
    row.append(
      heading,
      createElement("td", formatValue(field.value)),
      createSourceComparison(field),
    );
    tableBody.append(row);
  }
  table.append(tableHead, tableBody);
  scrollArea.append(table);
  section.append(scrollArea);
  return section;
}

function createRawRecords(meeting) {
  const section = createElement("details", undefined, "raw");
  section.append(createElement("summary", "Raw records and validation issues"));
  for (const record of meeting.records) {
    section.append(
      createElement(
        "h3",
        `${record.source.toUpperCase()} / row ${record.row} / ID ${formatValue(record.source_id)}`,
      ),
    );
    for (const issue of record.issues)
      section.append(createElement("p", issue, "issue"));
    for (const note of record.normalization_notes)
      section.append(createElement("p", note));
    section.append(createElement("pre", JSON.stringify(record.raw, null, 2)));
  }
  return section;
}

function createMeeting(meeting) {
  const section = createElement("details", undefined, "meeting");
  section.id = `meeting-${meeting.id}`;
  section.append(createMeetingSummary(meeting));
  const body = createElement("div", undefined, "meeting-body");
  body.append(
    createElement("h3", "Reconciliation decision"),
    createElement("p", explainMatch(meeting)),
    createElement(
      "p",
      `Sources: ${meeting.sources.map((source) => source.toUpperCase()).join(" + ")}`,
    ),
  );
  if (meeting.duplicate_count) {
    body.append(
      createElement(
        "p",
        `${meeting.duplicate_count} exact duplicate records combined. All originals are kept below.`,
      ),
    );
  }
  const reasons = createReviewReasons(meeting);
  if (reasons.childElementCount)
    body.append(createElement("h3", "Why this needs review"), reasons);
  for (const candidate of meeting.candidates)
    body.append(createCandidate(candidate));
  body.append(createFieldTable(meeting), createRawRecords(meeting));
  section.append(body);
  return section;
}

function showMeetings(data) {
  const summary = data.summary;
  meetingTotals.replaceChildren();
  for (const [count, label] of [
    [summary.meetings, "meetings"],
    [summary.matched, "matched"],
    [summary.conflicts, "with conflicts"],
    [summary.review, "need review"],
  ]) {
    const total = createElement("span");
    total.append(
      createElement("strong", String(count)),
      document.createTextNode(label),
    );
    meetingTotals.append(total);
  }
  meetingList.replaceChildren(...data.meetings.map(createMeeting));
  statusMessage.textContent = `Showing ${data.total} of ${summary.meetings} meetings`;
  if (!data.total)
    meetingList.append(
      createElement("p", "No meetings match these filters.", "empty"),
    );
}

let requestController;
let searchTimer;

async function loadMeetings() {
  if (requestController) requestController.abort();
  const request = new AbortController();
  requestController = request;
  statusMessage.textContent = "Loading meetings...";
  try {
    const parameters = new URLSearchParams({
      q: searchInput.value,
      filter: filterControls.querySelector("input:checked").value,
    });
    const response = await fetch(`/api/meetings?${parameters}`, {
      signal: request.signal,
    });
    if (!response.ok) throw new Error(`Server returned ${response.status}`);
    const data = await response.json();
    if (!request.signal.aborted) showMeetings(data);
  } catch (error) {
    if (error.name === "AbortError") return;
    meetingList.replaceChildren();
    meetingTotals.textContent = "";
    statusMessage.textContent = `Unable to load meetings. ${error.message}. Check the server and select Refresh view.`;
  }
}

function scheduleSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadMeetings, 180);
}

function refreshMeetings() {
  clearTimeout(searchTimer);
  loadMeetings();
}

function applyMeetingFilter() {
  const selected = filterControls.querySelector("input:checked");
  filterLabel.textContent = selected.nextElementSibling.textContent;
  filterMenu.open = false;
  filterToggle.focus();
  refreshMeetings();
}

function closeFilterMenu(event) {
  if (event.key === "Escape" && filterMenu.open) {
    event.preventDefault();
    filterMenu.open = false;
    filterToggle.focus();
  } else if (event.type === "click" && !filterMenu.contains(event.target)) {
    filterMenu.open = false;
  }
}

searchInput.addEventListener("input", scheduleSearch);
filterControls.addEventListener("change", applyMeetingFilter);
filterControls.addEventListener("click", (event) => {
  if (event.target.matches("input")) {
    // Choosing the already selected option should also dismiss the dropdown.
    filterMenu.open = false;
    filterToggle.focus();
  }
});
document.addEventListener("click", closeFilterMenu);
document.addEventListener("keydown", closeFilterMenu);
refreshButton.addEventListener("click", refreshMeetings);
loadMeetings();
