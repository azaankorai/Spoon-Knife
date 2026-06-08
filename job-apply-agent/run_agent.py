#!/usr/bin/env python3
"""Generate tailored job-application drafts via the Claude API.

Reads job-apply-agent/resume.md and one or more postings from
job-apply-agent/jobs/, asks Claude to assess fit and draft a cover letter +
summary for each, and writes the result to job-apply-agent/output/.

Requires the ANTHROPIC_API_KEY environment variable. Select which posting(s)
to process with the JOB_FILE environment variable: a filename inside jobs/,
or "all" (default) to process every posting.
"""
import os
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent
JOBS_DIR = ROOT / "jobs"
OUTPUT_DIR = ROOT / "output"

SYSTEM_PROMPT = """\
You help a job seeker prepare tailored, honest application materials from
markdown inputs. You never invent experience, credentials, or numbers that
aren't in the resume - your job is to select and phrase truthfully, not to
embellish.

You will be given the candidate's resume, a cover-letter template, an
application-summary template, and one job posting. Compare the posting's
responsibilities/requirements against the resume's skills, experience, and
attributes. Identify strong matches, partial matches (with an honest framing),
and real gaps - name gaps plainly rather than papering over them.

Pick the resume points that most directly support this specific posting,
preferring ones with measurable outcomes and ones whose language overlaps with
the posting (mirror accurate terminology, don't keyword-stuff). Draft a concise
cover letter (3-4 short paragraphs) following the cover-letter template,
grounded only in what's actually in the resume.

Fill out the application-summary template completely for this job. Reply with
ONLY the filled-in markdown for the summary file (including the embedded cover
letter) - no extra commentary, no code fences, no preamble.
"""

USER_PROMPT_TEMPLATE = """\
## Resume

{resume}

## Cover letter template

{cover_letter_template}

## Application summary template

{summary_template}

## Job posting ({job_filename})

{job_posting}

Produce the completed application summary (with the cover letter filled in)
for this posting, following the templates and the constraints above.
"""


def load(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def process_job(client: anthropic.Anthropic, job_path: Path, resume: str,
                cover_letter_template: str, summary_template: str) -> Path:
    user_prompt = USER_PROMPT_TEMPLATE.format(
        resume=resume,
        cover_letter_template=cover_letter_template,
        summary_template=summary_template,
        job_filename=job_path.name,
        job_posting=load(job_path),
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{job_path.stem}-summary.md"
    out_path.write_text(text.strip() + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    job_arg = os.environ.get("JOB_FILE", "all").strip()

    if job_arg and job_arg.lower() != "all":
        job_paths = [JOBS_DIR / job_arg]
    else:
        job_paths = sorted(JOBS_DIR.glob("*.md"))

    missing = [p for p in job_paths if not p.is_file()]
    for p in missing:
        print(f"::error::Job posting not found: {p}", file=sys.stderr)
    job_paths = [p for p in job_paths if p.is_file()]

    if not job_paths:
        print("::error::No job postings to process.", file=sys.stderr)
        return 1

    resume = load(ROOT / "resume.md")
    cover_letter_template = load(ROOT / "templates" / "cover-letter.md")
    summary_template = load(ROOT / "templates" / "application-summary.md")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    for job_path in job_paths:
        out_path = process_job(client, job_path, resume, cover_letter_template,
                               summary_template)
        print(f"Wrote {out_path.relative_to(ROOT.parent)}")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
