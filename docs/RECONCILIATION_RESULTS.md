# Review of the supplied data

All 42 input rows are retained. No same-source records were asserted to be exact duplicates. The final result contains 29 entries and 13 automatic pairs.

## Automatic pairs

| CRM | Calendar | Main evidence |
|---|---|---|
| CRM-1001 | CAL-A1 | David Park email + Sarah Chen + same local time |
| CRM-1002 | CAL-A2 | Mark Johnson email + Sarah Chen + same local time |
| CRM-1006 | CAL-A7 | Sarah Chen + pipeline/review topics + same local time |
| CRM-1008 | CAL-A9 | Lisa Tran email + James Wu + repaired legacy date/time; review warning |
| CRM-1009 | CAL-A10 | Sarah Chen + board/prep topics + same local time; cancellation conflict |
| CRM-1011 | CAL-A12 | Elena Marcos email + James Wu + same local time |
| CRM-1012 | CAL-A13 | Thomas Grant email + Sarah Chen + same local time |
| CRM-1013 | CAL-A14 | Sarah Chen attendee + advisory/committee/prep topics + same local time |
| CRM-1014 | CAL-A15 | Michael Reeves email + James Wu + same local time |
| CRM-1015 | CAL-A16 | Lisa Tran email + James Wu + same local time; invalid extra email flagged |
| CRM-1017 | CAL-A20 | James Wu + closing/dinner topics + same local time; invalid attendee placeholder flagged |
| CRM-1018 | CAL-A21 | Patricia Langley email + Sarah Chen + same local time |
| CRM-1019 | CAL-A22 | Sarah Chen + quarterly/business/review topics in description + same local time |

Every pair has differing title wording, so each is marked as having at least one field conflict. This is intentional transparency, not proof the pair is wrong. CRM-1001 also has completed/confirmed status disagreement. CRM-1009 has cancelled/confirmed disagreement. Status disagreements require review.

## Retained separately with review candidates

| Records | Reason |
|---|---|
| CRM-1004, CAL-A4 | UTC vs timezone-unspecified start; no offset invented |
| CRM-1005, CAL-A5, CAL-A6 | Two competing Pinnacle candidates; calendar rows look like duplicates but differ |
| CRM-1007, CAL-A8 | CRM start time missing |
| CRM-1016, CAL-A17 | Two-hour difference exceeds automatic window |

These nine standalone entries, plus five matched entries with validation/status issues (CRM-1001, CRM-1008, CRM-1009, CRM-1015, CRM-1017), produce **14 review entries**.

## Legitimate source-only entries

CRM-1003, CRM-1010, CRM-1020, CAL-A3, CAL-A18, CAL-A11, CAL-A19 have no eligible counterpart under this policy. Missing optional fields are displayed rather than treated as a failed ingestion. CAL-A3 and CAL-A18 are different weekly occurrences and remain separate. CAL-A11's minute-precision end time is valid ISO datetime input.

These outcomes are inspectable policy decisions and regression expectations. The assessment provides no authoritative pair labels. A reviewer can reasonably choose different ambiguity/time policies, but should not hide them or discard their supporting raw data.
