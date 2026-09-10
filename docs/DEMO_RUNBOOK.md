# Demo runbook — running reviewer carriers live

Everything below is verified working on this machine (last checked 2026-09-10, live FMCSA fetch confirmed).
Keep this open on a second screen during the walkthrough.

---

## 0. The one thing to remember

There is **one folder** you drop their files into and **one command** you run:

```powershell
# their files go here:
samples\reviewer\

# then:
python -m rater.book samples\reviewer
```

Everything else on this page is prep, variations on that, and what to say when something looks odd.

---

## 1. The night before

Run the full reproduce pass. It takes a few minutes and proves nothing has rotted:

```powershell
cd C:\Users\sophi\trucking-rater\trucking-rater
python run_all.py
```

Wait for `ALL STEPS OK` on the last line. If any step fails, fix it before the call — do not discover it live.

Then confirm **live** enrichment works, because that is the path the demo runs on:

```powershell
$env:RATER_OFFLINE = "0"
python -m rater samples\submissions\00_established_clean_ia.json
```

Look for `"enrichment_source": "live"` in the output. If it says `cache` or `fixture`, that carrier was
already cached — fine, but test an uncached DOT to be sure the webKey still works (any DOT with no file in
`data/cache/carrier/`).

If live fails, the demo still runs: everything falls back to cache/segment defaults and the carrier is
**referred under R02**, not crashed and not declined. Say that out loud if it happens — it is a designed
behaviour, and R02 exists exactly for this.

Create the landing folder now so it is not a fumble later:

```powershell
mkdir samples\reviewer
```

---

## 2. Fifteen minutes before

```powershell
cd C:\Users\sophi\trucking-rater\trucking-rater
$env:RATER_OFFLINE = "0"      # live mode — set once, lasts for this terminal window only
git status                    # should be clean, so anything new during the demo is obviously theirs
```

Notes on the environment:

- **No venv activation needed.** This project runs on the system Python (3.12.4 at `C:\Python312`), where the
  dependencies are installed. The `.venv` folder in the repo is not what you have been using — ignore it.
- `$env:RATER_OFFLINE` is per-terminal. If you open a new tab or PowerShell window mid-demo, **set it again**,
  or you will silently be running against fixtures and every unseen carrier will refer under R02.
- Have a second terminal already `cd`'d into the repo as a spare.

Warm up the console so the first live call is not the slow one:

```powershell
python -m rater samples\submissions\00_established_clean_ia.json
```

---

## 3. When they hand you the examples

They will do it in one of four ways. Each has an exact recipe.

### A. They send files (JSON / JSONL / CSV — any shape)

1. Save the attachments into `samples\reviewer\`. Do not rename them, do not open and "fix" them.
2. Run:

```powershell
python -m rater.book samples\reviewer
```

The ingest resolves aliases and container shapes on its own — a JSON object, a JSON array, a `.jsonl` feed, a
`.csv` with one row per carrier, or a submission nested one level down (`{"carrier": {...}}`) all work. This is
what `samples\reviewer_formats\` exists to prove; you can show that folder if they ask whether you anticipated
their format.

To hand them artifacts afterwards:

```powershell
python -m rater.book samples\reviewer --csv data\derived\book_check_reviewer.csv --jsonl data\derived\book_check_reviewer.jsonl
```

### B. They paste JSON into the chat

```powershell
notepad samples\reviewer\their_carrier.json      # paste, save, close
python -m rater samples\reviewer\their_carrier.json
```

`python -m rater <file>` gives the **full single-carrier breakdown** — every relativity, the credibility
weight, the loadings, the implied loss ratio. That is the one you want on screen when they ask "why that
number?". `python -m rater.book <folder>` gives the portfolio summary. Use both.

### C. They read DOT numbers out loud

Fastest path — only `usdot` is required, everything else defaults from the FMCSA record with the assumption
recorded in `flags`:

```powershell
'{"submission_id":"live1","usdot":1234567}' | Out-File -Encoding utf8 samples\reviewer\live1.json
python -m rater samples\reviewer\live1.json
```

For several at once, a CSV is quicker to type than several JSON files:

```powershell
@'
dot_number,power_units,driver_count,radius_miles,cargo,state,limit
1234567,2,2,300,dry van,TX,1m
7654321,4,5,600,reefer,GA,1m
'@ | Out-File -Encoding utf8 samples\reviewer\live.csv
python -m rater.book samples\reviewer\live.csv
```

(The closing `'@` must sit at column 0 — no indentation — or PowerShell will not parse it.)

### D. They want to see the whole book, not one carrier

```powershell
python -m rater.book samples\submissions_real          # 45 census-drawn carriers
python -m rater.book samples\submissions_holdout samples\submissions_operating   # 68 cold-start carriers (30 + 38)
python -m rater.book samples\submissions_real samples\submissions_holdout samples\reviewer   # all together
```

`samples\submissions_holdout` (30) plus `samples\submissions_operating` (38) is the strongest pair to lead with —
68 cold-start carriers, which is precisely the test they said they would run.

---

## 4. Reading the output out loud

The book check prints, in order: counts, decline and refer rates, min-premium binding count, the premium
distribution (total policy **and** per power unit), the histogram of rules fired, every errored submission with
its reason, then one line per submission.

Suggested narration, in this order:

1. **"Nothing errored"** — or, if something did, read the reason off the screen; an unreadable file is
   reported and the run continues.
2. **The three-way split** — priced / referred / declined. Refer is not a decline; it is a price with a human
   in the loop.
3. **The rules histogram** — name the rule that fired most and why it exists.
4. **The per-unit distribution** — and how many sat at the $8,000 per-unit floor. `min_premium_binding` tells
   you how much of the book is priced by the floor rather than by the loss cost.

Then drill into one carrier with `python -m rater <file>` and walk the breakdown top to bottom:
base loss cost per unit → relativities → credibility → ALAE → loadings → floor → policy fee.

---

## 5. Failure playbook

Have these answers ready. Each is a designed behaviour, not a bug — say so, and say which rule.

| What you see | What it means | What to say |
|---|---|---|
| `decline` with **D31** | Declared units differ from the census by more than 3, or by more than 2×. Very likely on a made-up unit count, or on a carrier whose MCS-150 is stale. | "That is the misrepresentation check. The census says one power unit and the submission says three — I want a human to reconcile that before I take the risk. Note it still computed the price: `premium_if_written`." |
| `refer` with **R02** | Enrichment degraded — priced on segment defaults. Means the API did not answer, or there is no key, or the DOT is unknown. | "The API did not answer. It priced on segment defaults and referred rather than declining or crashing — a thin-data carrier still gets a number." |
| `refer` with **R08** | DOT absent from the census snapshot: new registration or inactive. | "New or inactive registration. I can price it, but I want to see the filing first." |
| `error` on a file | Unreadable input. The run continues and reports it. | "That file is malformed — here is the reason it printed. The book check does not abort on one bad file." |
| Everything refers | You are almost certainly in offline mode. | Check `$env:RATER_OFFLINE`. Set it to `"0"` and re-run. |
| A number looks wrong | | Open `config\rates.yaml`. Every factor is tagged **[E]** estimated, **[S]** selected, or **[B]** benchmark-anchored, with the evidence in a comment beside it. `docs\RATING_MANUAL.md` is rendered from that file, so the manual cannot drift from the code. |

Two dormant rules you should disclose before they find them: **D24** (BASIC percentiles — FMCSA does not
publish them for property carriers) and **R06** (chameleon carriers — a stub). Both are in the gap register
in `docs\DELIVERABLES.md`. Volunteering these reads as command of the system; being caught on them does not.

---

## 6. After the call

Live runs write new files into `data/cache/carrier/` — one per carrier they gave you. That is expected.

```powershell
git status                    # shows the new cache entries + samples\reviewer\
```

Keep them: committing the reviewer submissions and their cache entries means the exact demo reproduces
offline afterwards, which is a good follow-up email.

```powershell
git add samples\reviewer data\cache\carrier
git commit -m "Add the carriers from the walkthrough and their cached enrichment"
$env:RATER_OFFLINE = "1"
python -m rater.book samples\reviewer     # proves it reproduces with no network
```

---

## Command card

```powershell
cd C:\Users\sophi\trucking-rater\trucking-rater
$env:RATER_OFFLINE = "0"                          # live. per-terminal. re-set in every new window.

python -m rater <file.json>                       # one carrier, full breakdown
python -m rater.book <folder-or-files>            # book summary
python -m rater.book <folder> --csv out.csv       # + machine-readable
python run_all.py                                 # everything, offline
```
