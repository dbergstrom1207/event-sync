# Project preferences

- Prioritize reconciliation logic and code that is easy to read.
- Keep the page simple and professionally finished: search, filters, an orderly meeting list, and details opened on demand. Simplicity should still include consistent alignment, spacing, and well-finished controls.
- Use neutral colors and a familiar sans-serif font. Avoid decorative typography, promotional headers, and oversized colored panels.
- Keep meeting filters inside one dropdown, initially labeled All meetings. Keep a gap between the trigger and the option panel so both borders stay complete.
- Keep the meeting filter dropdown beside Refresh view, including on small screens.
- Align client names and statuses in consistent columns across meeting rows. Avoid decorative status dots. Give summary numbers more prominence than their labels.
- Clearly distinguish an expanded meeting with a high-contrast header. Indent its details beneath it so the parent and child content are easy to separate.
- Use readable text of at least 17px. Avoid decorative headers, tiny labels, and repeated badges.
- Use names that describe the work, such as `normalize_record`, `find_match_reason`, and `loadMeetings`.
- Prefer ordinary control flow and small, purposeful functions. Avoid compressed expressions and unnecessary abstractions.
- Keep source values, matching reasons, conflicts, and uncertain cases inspectable.
- Run the Python tests after logic changes and the browser smoke test after interaction changes.
