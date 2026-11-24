#!/usr/bin/env python3
"""Build a tailored CV and/or cover letter from <folder>/spec.json.
  python3 scripts/build_application.py <company-folder> [--cv] [--letter] [--verify] [--spec FILE] [--out-dir DIR] [--force] [--workspace DIR]
No --cv/--letter: builds whichever sections exist in the spec. Existing output is never overwritten unless --force.
Spec format: docs/build-application.md (in the workspace)"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jobprofile import ProfileError, add_workspace_arg, load_profile  # noqa: E402
from lib import cvbuild as cb  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('folder', help='company folder (relative to the workspace root, or absolute)')
ap.add_argument('--cv', action='store_true')
ap.add_argument('--letter', action='store_true')
ap.add_argument('--verify', action='store_true', help='run verify_pdf.py + verify_layout.py (+ keyword coverage)')
ap.add_argument('--spec', default='spec.json', help='spec file inside the folder (default spec.json; use spec-<role>.json for a 2nd role at the same company)')
ap.add_argument('--out-dir', help='write outputs here instead of the company folder (use for test rebuilds)')
ap.add_argument('--force', action='store_true', help='overwrite existing outputs')
ap.add_argument('--docx-only', action='store_true', help='skip PDF conversion and layout checks (used automatically when LibreOffice is not installed)')
add_workspace_arg(ap)
a = ap.parse_args()

try:
    prof = load_profile(a.workspace)
except ProfileError as e:
    sys.exit(str(e))

folder = a.folder if os.path.isabs(a.folder) else os.path.join(str(prof.workspace), a.folder)
spec_path = os.path.join(folder, a.spec)
if not os.path.exists(spec_path):
    sys.exit(f'No {a.spec} in {folder} - see docs/build-application.md')
spec = json.load(open(spec_path, encoding='utf-8'))
out_dir = a.out_dir or folder
do_cv = a.cv or (not a.letter and 'cv' in spec)
do_letter = a.letter or (not a.cv and 'letter' in spec)
docx_only = a.docx_only or not cb.soffice_available()
if docx_only and not a.docx_only:
    print('WARNING: LibreOffice (soffice) not found - building DOCX only. Page fit and layout are NOT checked; install LibreOffice and rebuild with --force for the full check.')
status = 0
if do_cv:
    r = cb.build_cv(prof, spec, out_dir, folder, a.force, docx_only)
    print(f"CV: {'DOCX only, page count unknown' if r.get('docx_only') else str(r['pages']) + ' page(s)'}, ok={r['ok']} -> {r['pdf'] or r['docx']}")
    for i, t in r['dropped']:
        print(f"  cut p{i}: {t}")
    if a.verify:
        ok, rep = cb.verify(prof, 'cv', r, spec)
        print(rep)
        r['ok'] = r['ok'] and ok
    status |= 0 if r['ok'] else 1
if do_letter:
    r = cb.build_letter(prof, spec, out_dir, folder, a.force, docx_only)
    print(f"Letter: {'DOCX only, page count unknown' if r.get('docx_only') else str(r['pages']) + ' page(s)'}, {r['chars']} chars, ok={r['ok']} -> {r['pdf'] or r['docx']}")
    if a.verify:
        ok, rep = cb.verify(prof, 'letter', r, spec)
        print(rep)
        r['ok'] = r['ok'] and ok
    status |= 0 if r['ok'] else 1
# exit 0 = fully verified, 1 = a check failed, 2 = built DOCX only (PDF and layout unchecked)
sys.exit(status or (2 if docx_only else 0))
