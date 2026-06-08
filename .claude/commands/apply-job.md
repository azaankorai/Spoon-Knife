---
description: Generate a tailored cover letter and match summary for a job posting via the job-apply-agent
---

Use the `job-apply-agent` subagent to prepare tailored application materials.

Target posting(s): $ARGUMENTS

- If a filename (or partial name) was given above, find the matching file in
  `job-apply-agent/jobs/` and process only that one.
- If `_inbox.md` has new lead entries below its template (job title/company/link
  + pasted description text), turn each one into a proper posting `.md` file in
  `job-apply-agent/jobs/` first (using the same structure as the existing postings),
  then remove the entry from `_inbox.md` once its posting file exists.
- Otherwise, process every posting in `job-apply-agent/jobs/` (excluding `_inbox.md`
  itself and the `example-*` template files) that does not already have a
  corresponding `*-summary.md` file in `job-apply-agent/output/`.

For each posting processed, write `job-apply-agent/output/<job-file-stem>-summary.md`
following `templates/application-summary.md` (match assessment, suggested resume
emphasis, and a tailored cover letter per `templates/cover-letter.md`), grounded
strictly in `job-apply-agent/resume.md` — no invented experience, interests, or
numbers. Finish with a one-line verdict (Strong/Good/Partial match) per posting and
the output file path.
