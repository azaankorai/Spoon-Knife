# Job Leads Inbox

Paste job links/descriptions you find here. For each one you're interested in, add an
entry below using this format — then ask Claude Code (or run `/apply-job`) to
"process the leads in this inbox" and it will turn each entry into a proper posting
file in `job-apply-agent/jobs/` and generate tailored materials for it.

Why paste the description text too, not just the link? Most job sites (SEEK, Indeed,
company career pages) block automated tools from reading their pages, so the agent
can't fetch the posting itself — pasting the text lets it actually compare the role
against your resume.

---

## Lead template (copy this block for each new lead)

### {{Job title}} — {{Company}}

- **Link:** {{paste the URL here}}
- **Location:** {{suburb, e.g. Merrylands NSW}}

{{Paste the job description / responsibilities / requirements text here}}

---

<!-- Add your leads below this line -->
