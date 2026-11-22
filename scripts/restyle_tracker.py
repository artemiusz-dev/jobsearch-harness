#!/usr/bin/env python3
"""
restyle_tracker.py
------------------
Sorts, styles, and verifies the applications tracker (paths.tracker in profile.yaml).

Usage (from the workspace, or pass --workspace):
    python3 scripts/restyle_tracker.py

Actions:
  1. Backs up the current file to paths.backup_dir with a timestamp.
  2. Sorts rows by status priority (tracker.statuses order), then by Updated date descending.
  3. Renumbers the # column.
  4. Applies all styling (header, status colours, column widths, borders, freeze).
  5. Prints a summary and exits with code 1 on any verification failure.
"""

import argparse
import datetime
import os
import shutil
import sys

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jobprofile import ProfileError, add_workspace_arg, load_profile  # noqa: E402

BASE_WIDTHS = {
    "#": 4, "Company": 24, "Role": 36, "Source": 22, "Status": 14, "Match %": 10,
    "Applied": 12, "Intro Call": 12, "Assignment": 12, "Tech Interview": 14, "Final Interview": 14,
    "Offer / Rejected": 16, "Next Action": 44, "Folder": 28, "Updated": 12,
}


def thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)


def hex6(c, default):
    return (c or default).lstrip("#").upper()


def parse_date(val):
    if val is None:
        return datetime.date.min
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val if isinstance(val, datetime.date) and not isinstance(val, datetime.datetime) else val.date()
    try:
        return datetime.datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
    except Exception:
        return datetime.date.min


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_workspace_arg(ap)
    a = ap.parse_args()
    try:
        prof = load_profile(a.workspace)
    except ProfileError as e:
        sys.exit(str(e))

    tracker = str(prof.path("tracker"))
    backup_dir = str(prof.path("backup_dir"))
    sheet = prof["tracker"]["sheet"]
    statuses = prof.statuses
    order = [s["name"] for s in statuses]
    styles = {s["name"]: {"bg": hex6(s.get("color"), "#FFFFFF"), "text": hex6(s.get("text_color"), "#1A1A1A")} for s in statuses}
    dimmed = {s["name"] for s in statuses if s.get("dimmed")}
    widths = dict(BASE_WIDTHS)
    widths[prof.salary_column] = 34

    if not os.path.exists(tracker):
        print(f"ERROR: tracker not found at {tracker}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(backup_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(tracker))[0]
    dest = os.path.join(backup_dir, f"{stem}_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx")
    shutil.copy2(tracker, dest)
    print(f"Backup saved: {dest}")

    wb = openpyxl.load_workbook(tracker)
    if sheet not in wb.sheetnames:
        print(f"ERROR: sheet '{sheet}' not found.", file=sys.stderr)
        sys.exit(1)
    ws = wb[sheet]

    headers = [cell.value for cell in ws[1]]

    def col(name):
        return headers.index(name) + 1  # 1-based

    num_col, status_col, updated_col = col("#"), col("Status"), col("Updated")

    def status_rank(v):
        val = str(v).strip() if v else ""
        return order.index(val) if val in order else len(order)

    data_rows = [list(row) for row in ws.iter_rows(min_row=2, values_only=True) if any(v is not None for v in row)]
    data_rows.sort(key=lambda r: (status_rank(r[status_col - 1]), -parse_date(r[updated_col - 1]).toordinal()))

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.value = None
    for i, row_data in enumerate(data_rows, start=1):
        row_data[num_col - 1] = i
        for j, val in enumerate(row_data, start=1):
            ws.cell(row=i + 1, column=j).value = val

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(name="Calibri", bold=True, size=10, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 32
    for cell in ws[1]:
        cell.fill, cell.font, cell.alignment, cell.border = header_fill, header_font, header_align, thin_border()

    body_default = Font(name="Calibri", size=9, color="1A1A1A")
    body_dimmed = Font(name="Calibri", size=9, color="AAAAAA")
    wrap_col = headers.index("Next Action") + 1 if "Next Action" in headers else -1

    for row_idx in range(2, len(data_rows) + 2):
        status_val = str(ws.cell(row=row_idx, column=status_col).value or "").strip()
        st = styles.get(status_val, {"bg": "FFFFFF", "text": "1A1A1A"})
        fill = PatternFill("solid", fgColor=st["bg"])
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.fill = fill
            cell.border = thin_border()
            cell.alignment = Alignment(vertical="top", wrap_text=(col_idx == wrap_col))
            if col_idx == status_col:
                cell.font = Font(name="Calibri", size=9, bold=True, color=st["text"])
            else:
                cell.font = body_dimmed if status_val in dimmed else body_default

    for header_name, width in widths.items():
        if header_name in headers:
            ws.column_dimensions[get_column_letter(headers.index(header_name) + 1)].width = width

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(tracker)

    ws2 = openpyxl.load_workbook(tracker)[sheet]
    row_count = sum(1 for row in ws2.iter_rows(min_row=2, values_only=True) if any(v is not None for v in row))
    if row_count != len(data_rows):
        print(f"ERROR: row count changed ({len(data_rows)} -> {row_count})", file=sys.stderr)
        sys.exit(1)
    print(f"Restyled: {tracker} ({row_count} rows)")
    print("Verification passed.")


if __name__ == "__main__":
    main()
