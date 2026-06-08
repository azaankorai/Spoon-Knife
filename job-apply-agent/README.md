# Job Apply Agent

A small markdown-driven toolkit for preparing tailored job application materials with
Claude Code. It reads your resume and a job posting (both plain markdown), assesses
fit, and drafts a cover letter and application summary for you to review and send.

**It does not submit applications anywhere.** Auto-submitting applications to job
boards/ATSes typically violates their terms of service and produces low-quality, easy
-to-spot spam. This toolkit only prepares materials — you stay in control of what
gets sent and where.

## Layout

```
job-apply-agent/
├── resume.md                     # Your resume (replace the placeholder!)
├── jobs/                         # One .md file per job posting you're considering
│   ├── example-backend-engineer.md
│   └── example-fullstack-engineer.md
├── templates/
│   ├── cover-letter.md           # Structure the agent follows for cover letters
│   └── application-summary.md    # Structure for the per-job output file
└── output/                       # Generated summaries + draft cover letters land here
```

The agent itself is defined at `.claude/agents/job-apply-agent.md`.

## Setup

1. Replace `job-apply-agent/resume.md` with your real resume (keep it in markdown —
   sections like Summary, Skills, Experience, Education work well).
2. For each job you're considering, save the posting as a new `.md` file in
   `job-apply-agent/jobs/`. Copy the structure of the example files (title, company,
   location, responsibilities, requirements) — the agent works best when the posting
   text is there for it to compare against.

## Usage

In Claude Code, ask the `job-apply-agent` subagent to process one or more postings,
e.g.:

> Use the job-apply-agent to prepare materials for
> job-apply-agent/jobs/example-backend-engineer.md

For each posting, the agent will:

1. Compare the posting's requirements against your resume (matches, partial matches,
   and honest gaps — it won't invent experience to paper over a gap).
2. Pick the resume bullets that best support that specific role.
3. Draft a tailored cover letter.
4. Write an `application-summary.md`-style file to `job-apply-agent/output/` with the
   match assessment, suggested resume emphasis, and the draft cover letter.

Review everything in `output/` before you actually apply — the agent prepares drafts,
it doesn't replace your judgment about what to send.

## Run it from GitHub Actions ("Run workflow" button)

You can also generate drafts without opening Claude Code, via the
**Run Job Apply Agent** workflow (`.github/workflows/job-apply-agent.yml`):

1. **One-time setup:** add an `ANTHROPIC_API_KEY` repository secret — go to
   *Settings → Secrets and variables → Actions → New repository secret*. Get a key
   at https://console.anthropic.com/.
2. Go to the **Actions** tab → **Run Job Apply Agent** → **Run workflow**.
3. Optionally enter the filename of a single posting from `job-apply-agent/jobs/`
   (e.g. `retail-sales-assistant-parramatta.md`); leave it as `all` to process every
   posting in that folder.
4. Click **Run workflow**. It calls the Claude API to generate a tailored cover
   letter + match summary for each selected posting, writes them to
   `job-apply-agent/output/`, and commits the results back to the branch.

This is just a remote way to run the same generation step — it still only produces
draft files for you to review; nothing gets submitted anywhere automatically.
