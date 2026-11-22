"""Spec-driven CV and cover-letter builder (replaces per-company generator scripts).

CV: edits the untouched base CV (paths.base_cv) and drops low-value paragraphs progressively until the PDF
fits max_pages and the layout check is clean. The base CV structure is found by section headings
(profile cv_map), not by hardcoded paragraph numbers. Print the map with:
    python3 scripts/lib/cvbuild.py --map [--workspace DIR]
Letter: Calibri styling; name and contact come from the base CV.
"""
import atexit
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import docx
import pypdf
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobprofile import add_workspace_arg, load_profile  # noqa: E402

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DARK, ACCENT, MED = RGBColor(0x1a, 0x1a, 0x1a), RGBColor(0x2b, 0x57, 0x97), RGBColor(0x55, 0x55, 0x55)
EM_DASH = chr(0x2014)
LAYOUT_SKIPPED = 3          # verify_layout.py exit code: no usable extractor, not a verdict
SOFFICE_TIMEOUT = 180


# ---------------------------------------------------------------- text helpers
def settext(p, t):
    """Replace a paragraph's text, keeping the first run's formatting (adds a run if there is none)."""
    if not p.runs:
        p.add_run(t)
        return
    p.runs[0].text = t
    for r in p.runs[1:]:
        r.text = ''


def set_label_value(p, label, value):
    """Rewrite a 'Label: values' skills line. Keeps label/value runs when the line has two or more;
    folds into one run otherwise."""
    runs = p.runs
    if len(runs) >= 2:
        runs[0].text = label + ': '
        runs[1].text = value
        for r in runs[2:]:
            r.text = ''
    elif len(runs) == 1:
        runs[0].text = f'{label}: {value}'
    else:
        p.add_run(label + ': ').bold = True
        p.add_run(value)


def _strings(obj):
    """All string values nested in a spec fragment."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def _check_text(prof, *texts):
    if not prof['style']['forbid_em_dash']:
        return
    for t in texts:
        if EM_DASH in t:
            raise SystemExit('Em dash found in spec text; use a short dash "-" (style.forbid_em_dash is on)')


def _safe_name(name):
    """A spec file_name must be a plain file stem: no directories, no traversal."""
    if not name or name in ('.', '..') or os.path.basename(name) != name or '\\' in name or '/' in name:
        raise SystemExit(f'Invalid file_name {name!r}: use a plain file name without directories')
    return name


def company_slug(folder):
    """Folder name minus a trailing -YYYY-MM-DD."""
    return re.sub(r'-\d{4}-\d{2}-\d{2}$', '', os.path.basename(os.path.normpath(folder)))


# ---------------------------------------------------------------- pdf
_soffice_profile = None


def _profile_dir():
    """One throwaway LibreOffice user profile per process: avoids lock clashes with a running
    LibreOffice window and avoids re-initialising a profile for every conversion."""
    global _soffice_profile
    if _soffice_profile is None:
        _soffice_profile = tempfile.mkdtemp(prefix='soffice-profile-')
        atexit.register(shutil.rmtree, _soffice_profile, ignore_errors=True)
    return _soffice_profile


def to_pdf(docx_path, outdir, timeout=SOFFICE_TIMEOUT):
    pdf = os.path.join(outdir, os.path.basename(docx_path)[:-5] + '.pdf')
    if os.path.exists(pdf):
        os.remove(pdf)            # never mistake an earlier build for this one
    cmd = ['soffice', f'-env:UserInstallation={Path(_profile_dir()).as_uri()}', '--headless',
           '--convert-to', 'pdf', '--outdir', outdir, docx_path]
    try:
        r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError('LibreOffice `soffice` not found on PATH; install LibreOffice to build PDFs') from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'soffice did not finish within {timeout}s converting {docx_path}') from None
    if r.returncode != 0 or not os.path.exists(pdf):
        detail = (r.stderr or r.stdout or '').strip()[:500]
        raise RuntimeError(f'PDF conversion failed (exit {r.returncode}) for {docx_path}: {detail}')
    return pdf


def pages_of(pdf):
    return len(pypdf.PdfReader(pdf).pages)


def pdf_text(pdf):
    return '\n'.join((p.extract_text() or '') for p in pypdf.PdfReader(pdf).pages)


def layout_check(pdf):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'verify_layout.py'), pdf], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def guard_target(path, force):
    if os.path.exists(path) and not force:
        raise SystemExit(f'Refusing to overwrite existing file: {path}\n'
                         '  (submitted materials are immutable) use --out-dir DIR or --force')


# ---------------------------------------------------------------- base CV structure
def _is_heading_like(text):
    return bool(text) and len(text) <= 40 and ':' not in text and text.isupper()


def cv_map(prof, paragraphs):
    """Locate CV sections. Returns dict: name, title, contact, summary, summary_heading, skills_heading,
    skills (list of paragraph indices), experience_heading. Raises SystemExit with a helpful message.

    Layout rules: the first three non-empty paragraphs are name, title and contact line (override with
    cv_map.indices). Section headings are short paragraphs after that block containing the configured
    keyword. The skills block runs from its heading to the next heading, in either order of sections;
    other section headings must be short and UPPERCASE (or be the summary/experience heading)."""
    m = prof['cv_map']
    idx = m.get('indices', {})
    texts = [p.text.strip() for p in paragraphs]
    head = [i for i, t in enumerate(texts) if t]
    if len(head) < 3:
        raise SystemExit('Base CV needs at least three non-empty paragraphs (name, title, contact line)')
    name_i, title_i, contact_i = idx.get('name', head[0]), idx.get('title', head[1]), idx.get('contact', head[2])
    after_header = max(name_i, title_i, contact_i)

    def find(keyword):
        kw = keyword.lower()
        for i in range(after_header + 1, len(texts)):     # a heading is a short paragraph containing the keyword
            if len(texts[i]) <= 40 and kw in texts[i].lower():
                return i
        raise SystemExit(f"Base CV has no short section heading containing '{keyword}' below the header block. "
                         "Set cv_map.*_heading in profile.yaml (see: cvbuild.py --map).")

    sh, kh, eh = find(m['summary_heading']), find(m['skills_heading']), find(m['experience_heading'])
    if len({sh, kh, eh}) < 3:
        raise SystemExit('Summary, skills and experience headings must be three different paragraphs; '
                         'adjust cv_map.*_heading in profile.yaml')
    known = {sh, eh}
    skills = []
    for i in range(kh + 1, len(texts)):
        if i in known or _is_heading_like(texts[i]):
            break
        if texts[i]:
            skills.append(i)
    return {'name': name_i, 'title': title_i, 'contact': contact_i, 'summary_heading': sh,
            'summary': idx.get('summary', sh + 1), 'skills_heading': kh, 'skills': skills, 'experience_heading': eh}


def describe_map(prof):
    d = docx.Document(str(prof.path('base_cv')))
    P = d.paragraphs
    mp = cv_map(prof, P)
    print('Section map (paragraph indices are what spec "edits"/"drop" refer to):')
    for k in ('name', 'title', 'contact', 'summary_heading', 'summary', 'skills_heading', 'experience_heading'):
        print(f"  {k:<19} p{mp[k]}: {P[mp[k]].text[:60]!r}")
    print(f"  skills lines        p{mp['skills'][0]}..p{mp['skills'][-1]} ({len(mp['skills'])} lines)" if mp['skills'] else '  skills lines        none')
    print('\nAll paragraphs:')
    for i, p in enumerate(P):
        print(f"  p{i:<3} {p.text[:80]!r}")


# ---------------------------------------------------------------- CV
def _apply_cv(prof, c, ndrop):
    d = docx.Document(str(prof.path('base_cv')))
    P = d.paragraphs
    mp = cv_map(prof, P)
    if 'title' in c:
        settext(P[mp['title']], c['title'])
    if 'summary' in c:
        settext(P[mp['summary']], c['summary'])
    skills = c.get('skills')
    if skills is not None:
        slots = mp['skills']
        if len(skills) > len(slots):
            raise SystemExit(f'spec has {len(skills)} skills lines but the base CV skills block has {len(slots)}; '
                             'run cvbuild.py --map to see it')
        for i, (lab, val) in enumerate(skills):
            set_label_value(P[slots[i]], lab, val)
        for j in range(len(skills), len(slots)):         # unused skill lines are removed
            P[slots[j]]._p.getparent().remove(P[slots[j]]._p)
    for e in c.get('edits', []):
        p = P[e['p']]
        if 'text' in e:
            settext(p, e['text'])
        elif 'replace' in e:
            old, new = e['replace']
            if old not in p.text:
                raise SystemExit(f"edit p{e['p']}: '{old[:40]}' not found in the base paragraph")
            settext(p, p.text.replace(old, new))
        elif 'append' in e:
            settext(p, p.text.rstrip() + e['append'])
        else:
            raise SystemExit(f"edit p{e['p']}: need text | replace | append")
    prefixes = tuple(prof['cv_map'].get('keep_with_next_prefixes', []))
    auto = [i for i, p in enumerate(P) if prefixes and p.text.strip().startswith(prefixes)]
    for k in c.get('keep_with_next', auto):
        P[k].paragraph_format.keep_with_next = True
    for k in c.get('keep_together', []):
        P[k].paragraph_format.keep_together = True
    dropped = [(i, P[i].text[:70]) for i in c.get('drop', [])[:ndrop]]
    for i in c.get('drop', [])[:ndrop]:
        P[i]._p.getparent().remove(P[i]._p)
    return d, dropped


def build_cv(prof, spec, out_dir, folder, force=False):
    c = spec['cv']
    _check_text(prof, *_strings(c))
    name = _safe_name(c.get('file_name') or prof.output_stem(company_slug(folder), 'CV'))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + '.docx')
    guard_target(out, force)
    guard_target(out[:-5] + '.pdf', force)
    max_pages = c.get('max_pages', 2)
    for n in range(0, len(c.get('drop', [])) + 1):
        d, dropped = _apply_cv(prof, c, n)
        d.save(out)
        pdf = to_pdf(out, out_dir)
        pages = pages_of(pdf)
        rc, lay = layout_check(pdf)
        # rc 3 = no text extractor (Poppler) installed: not a verdict, so judge by page count alone
        good = pages <= max_pages and (rc == LAYOUT_SKIPPED or 'layout: clean' in lay)
        if good:
            break
    return dict(docx=out, pdf=pdf, pages=pages, dropped=dropped, layout=lay, layout_rc=rc, ok=good)


# ---------------------------------------------------------------- letter
def _run(p, text, size, color, bold=False):
    r = p.add_run(text)
    r.font.name = 'Calibri'
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.bold = bold
    r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')


def _para(d, align=None, after=0):
    p = d.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(0)
    if align is not None:
        p.alignment = align
    return p


def build_letter(prof, spec, out_dir, folder, force=False):
    L = spec['letter']
    base = docx.Document(str(prof.path('base_cv'))).paragraphs
    mp = cv_map(prof, base)
    name, contact = base[mp['name']].text, base[mp['contact']].text      # grounded in the base CV
    headline = L.get('headline') or spec.get('cv', {}).get('title') or base[mp['title']].text
    body = '\n\n'.join(L['paragraphs'])
    _check_text(prof, *_strings(L), headline)
    if 'max_chars' in L and len(body) >= L['max_chars']:
        raise SystemExit(f"letter body is {len(body)} chars, limit is under {L['max_chars']} (max_chars)")
    date = L.get('date') or datetime.date.today().strftime('%d %B %Y').lstrip('0')
    d = docx.Document()
    s = d.sections[0]
    s.page_width, s.page_height = Mm(210), Mm(297)
    for m in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
        setattr(s, m, Mm(19.05))
    st = d.styles['Normal']
    st.font.name = 'Calibri'
    st.font.size = Pt(11)
    c = WD_ALIGN_PARAGRAPH.CENTER
    _run(_para(d, c), name, 18, DARK, True)
    _run(_para(d, c), headline, 12, ACCENT)
    _run(_para(d, c, 8), contact, 10, MED)
    _run(_para(d, after=8), date, 11, MED)
    if L.get('re'):
        _run(_para(d, after=8), L['re'], 11, DARK, True)
    _run(_para(d, after=8), L.get('salutation', 'Dear Hiring Team,'), 11, DARK)
    for t in L['paragraphs']:
        _run(_para(d, after=8), t, 11, DARK)
    _run(_para(d), L.get('closing', 'Best regards,'), 11, DARK)
    _run(_para(d), prof['identity']['full_name'], 11, DARK, True)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, _safe_name(L.get('file_name') or prof.output_stem(company_slug(folder), 'Cover-Letter')) + '.docx')
    guard_target(out, force)
    guard_target(out[:-5] + '.pdf', force)
    d.save(out)
    pdf = to_pdf(out, out_dir)
    pages = pages_of(pdf)
    rc, lay = layout_check(pdf)
    return dict(docx=out, pdf=pdf, pages=pages, chars=len(body), layout=lay, layout_rc=rc, ok=(pages == 1))


# ---------------------------------------------------------------- verify
def verify(prof, kind, res, spec):
    """Run the mechanical PDF checks. Returns (ok, report)."""
    pdf = res['pdf']
    contains = [prof['identity']['email']] + list(spec.get(kind, {}).get('must_contain', []))
    sec = spec.get(kind, {})
    cmd = [sys.executable, os.path.join(SCRIPTS, 'verify_pdf.py'), pdf]
    if 'verify_pages' in sec:                       # explicit exact page count
        cmd += ['--pages', str(sec['verify_pages'])]
    elif kind == 'cv':                              # a CV may be shorter than its limit
        cmd += ['--max-pages', str(sec.get('max_pages', 2))]
    else:                                           # a letter is exactly one page
        cmd += ['--pages', '1']
    if kind == 'cv':
        cmd.append('--ascii-dates')
    for x in contains:
        cmd += ['--contains', x]
    r = subprocess.run(cmd, capture_output=True, text=True)
    report = [(r.stdout + r.stderr).strip(), res['layout']]
    ok = r.returncode == 0 and res['layout_rc'] in (0, LAYOUT_SKIPPED)
    kws = spec.get(kind, {}).get('keywords', [])
    if kws:
        txt = re.sub(r'\s+', ' ', pdf_text(pdf)).lower()
        rows = [f"  {'covered' if k.lower() in txt else 'MISSING (re-check with pdftotext -layout)'}: {k}" for k in kws]
        report.append('keyword coverage:\n' + '\n'.join(rows))
    return ok, '\n'.join(report)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', action='store_true', required=True)
    add_workspace_arg(ap)
    a = ap.parse_args()
    describe_map(load_profile(a.workspace))
