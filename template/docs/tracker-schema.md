# Applications Tracker Schema

File: `paths.tracker` (default `applications-tracker.xlsx`), sheet `tracker.sheet` (default `Pipeline`). Every column, status name and color below can be overridden in `profile.yaml` under `tracker`.

## Columns (in order)
`#` | `Company` | `Role` | `Source` | `Status` | `Match %` | `Salary (<currency> gross)` | `Applied` | `Intro Call` | `Assignment` | `Tech Interview` | `Final Interview` | `Offer / Rejected` | `Next Action` | `Folder` | `Updated`

- The salary column name uses `compensation.currency` (for example `Salary (EUR gross)`), or `tracker.salary_column` if set.
- `Folder` - the company folder name (for example `acme-senior-backend-2026-03-28`) for cross-referencing `analysis.md` and docs.
- Stage columns (`Applied` -> `Offer / Rejected`) hold a date (YYYY-MM-DD) when the stage is completed and stay blank otherwise.
- Scripts depend on the names `#`, `Company`, `Role`, `Status`, `Match %`, `Applied`, `Intro Call`, `Tech Interview`, `Final Interview`, `Offer / Rejected`, `Next Action`, `Updated`. Keep them.

## Valid status values (default)
| Status | Meaning | Row color |
|--------|---------|-----------|
| `BACKLOG` | Found, not yet analyzed | light grey |
| `To Apply` | Analyzed, ready to apply | light grey |
| `ANALYZING` | JD analysis in progress | blue |
| `SKIP` | Decided not to apply | red (dimmed) |
| `REFERRAL` | Applying via referral, pending submission | purple |
| `APPLYING` | CV tailoring / cover letter in progress | orange |
| `APPLIED` | Application submitted | orange |
| `CV SENT` | CV sent directly to a recruiter | orange |
| `SCREENING` | Recruiter / HR contact initiated | yellow |
| `INTERVIEW` | Technical or hiring-manager round | green |
| `OFFER` | Offer received | bright green |
| `REJECTED` | Rejected at any stage | red (dimmed) |
| `WITHDRAWN` | Withdrew or role filled | grey (dimmed) |

## Row sort order

Rows are sorted by `restyle_tracker.py` on every run.

**Primary sort:** status, most actionable first (the order of `tracker.statuses`; default):
`OFFER` -> `INTERVIEW` -> `SCREENING` -> `APPLYING` -> `REFERRAL` -> `APPLIED` -> `CV SENT` -> `ANALYZING` -> `To Apply` -> `BACKLOG` -> `SKIP` -> `REJECTED` -> `WITHDRAWN`

**Secondary sort:** `Updated` date descending.

The `#` column is renumbered after sorting.

## Row styling
- Header row: dark blue background (`#1F4E79`), white bold Calibri 10pt, height 32.
- Data rows: background and status text color from the status palette.
- Statuses marked `dimmed` (default `SKIP`, `REJECTED`, `WITHDRAWN`): all non-status cells dimmed to `#AAAAAA`.
- Status cell: bold, colored text matching the palette.
- All columns: Calibri 9pt, thin grey borders, frozen first row, autofilter on all columns.

## Column widths (approximate)
`#`=4 | Company=24 | Role=36 | Source=22 | Status=14 | Match%=10 | Salary=34 | stage columns=12-16 | Next Action=44 | Folder=28 | Updated=12

## Creating the file
`init-workspace` creates an empty tracker with these columns and styling. To rebuild from scratch, regenerate with openpyxl from the existing rows (never lose entries) and run `restyle_tracker.py`.
