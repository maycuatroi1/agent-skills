---
name: add-tasks
description: This skill should be used when the user asks to "add task", "them task", "tao task", "add todo with context", or gives a task that references a source URL (Google Sheets, Docs, GitHub issue, web page). Adds the todo via the `life` CLI and auto-manages context - fetches the source, extracts only the relevant rows/sections, then attaches the link plus a self-contained summary to the todo so it is workable later without re-opening the source.
version: 0.1.0
---

# add-tasks

Add a todo via the `life` CLI and automatically attach rich context. The goal: every task created from an external source must be self-contained - openable months later and workable without re-reading the source.

Requires the `life` CLI (see the `life-cli` skill for install and credentials).

## Workflow

1. **Parse the request** into title, `--due YYYY-MM-DD`, `--priority high|medium|low`, `--tags t1,t2`. Title stays in the user's language with full Vietnamese diacritics. Infer tags from the domain (project name, area).

2. **Fetch every referenced source** before adding the todo:
   - Google Sheets: export as CSV, do not scrape the HTML page:
     ```bash
     curl -sL "https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<GID>"
     ```
     `SHEET_ID` and `gid` come from the URL (`/d/<SHEET_ID>/edit?gid=<GID>`). If the sheet is private the export returns an HTML login page - fall back to asking the user to share it or paste the rows.
   - Google Docs: `https://docs.google.com/document/d/<DOC_ID>/export?format=txt`
   - GitHub issue/PR: `gh issue view <url>` / `gh pr view <url>`
   - Anything else: WebFetch with a prompt asking for the parts relevant to the task.

3. **Extract only what the task needs**, not the whole document. Example: if the task targets rows T2.1-T2.5 of a task sheet, keep those rows with their key columns (description, difficulty, estimate) plus any total the user will compare against. Drop unrelated rows.

4. **Add the todo and attach context**:
   ```bash
   life todo add "<title>" [--due D] [--priority P] [--tags T]
   # note the returned id N
   life todo context N url "<original source URL>"
   life todo context N add "<extracted summary>"
   life todo context N file <path>        # local files - auto-uploads to GCS
   ```
   Always attach BOTH the url and the text summary: the url for provenance, the summary so the task works even if the source changes or access is lost.

5. **Report back** with the todo id, what was attached, and a short table of the extracted data so the user can verify the extraction is correct.

## Summary format

One text context entry, dense but readable:

```
<Source name> - <scope>: <item 1 (key figures)>; <item 2 (...)>; ... Total/target: <figure>.
```

Include concrete numbers (estimates, counts, deadlines) - they are usually the reason the task exists. Use ASCII `-` and `->`, never em-dash or smart quotes.

## Gotchas

- `life todo context N add` takes the text as one argument - quote it; avoid double quotes inside, use `'` or rephrase.
- Multiple tasks from one source: one todo per actionable item, but reuse a single fetched copy of the source; attach the same url to each with item-specific summaries.
- If the source cannot be fetched (auth wall, 404), still add the todo and attach the url, then tell the user the summary is missing and why.
- Dates are Asia/Ho_Chi_Minh, format YYYY-MM-DD.

## See also

- `life-cli` skill - install, credentials, command discovery (`life todo --help`)
