"""Spec-driven CV and cover-letter builder (replaces per-company generator scripts).

CV: edits the untouched base CV (paths.base_cv) and drops low-value paragraphs progressively until the PDF
fits max_pages and the layout check is clean. The base CV structure is found by section headings
(profile cv_map), not by hardcoded paragraph numbers. Print the map with:
    python3 scripts/lib/cvbuild.py --map [--workspace DIR]
Letter: Calibri styling; name and contact come from the base CV.
"""
import datetime
import os
import re
import subprocess
import sys

import docx
import pypdf
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobprofile import add_workspace_arg, load_profile  # noqa: E402

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DARK, ACCENT, MED = RGBColor(0x1a, 0x1a, 0x1a), RGBColor(0x2b, 0x57, 0x97), RGBColor(0x55, 0x55, 0x55)


def settext(p, t):
    p.runs[0].text = t
    for r in p.runs[1:]:
        r.text = ''


def to_pdf(docx_path, outdir):
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', outdir, docx_path],
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(outdir, os.path.basename(docx_path)[:-5] + '.pdf')
    if not os.path.exists(pdf):
        raise RuntimeError('PDF conversion failed (is LibreOffice `soffice` installed?): ' + pdf)
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


def _check_text(prof, *texts):
    if not prof['style']['forbid_em_dash']:
        return
    for t in texts:
        if '—' in t:
            raise SystemExit('Em dash found in spec text; use a short dash "-" (style.forbid_em_dash is on)')


def company_slug(folder):
    """Folder name minus a trailing -YYYY-MM-DD."""
    return re.sub(r'-\d{4}-\d{2}-\d{2}$', '', os.path.basename(os.path.normpath(folder)))


# ---------------------------------------------------------------- base CV structure
def cv_map(prof, paragraphs):
    """Locate CV sections. Returns dict: name, title, contact, summary, summary_heading, skills_heading,
    skills (list of paragraph indices), experience_heading. Raises SystemExit with a helpful message."""
    m = prof['cv_map']
    idx = m.get('indices', {})
    texts = [p.text.strip() for p in paragraphs]

    def find(prefix):
        pre = prefix.lower()
        for i, t in enumerate(texts):          # a heading is a short paragraph containing the keyword
            if len(t) <= 40 and pre in t.lower():
                return i
        raise SystemExit(f"Base CV has no short section heading containing '{prefix}'. "
                         "Set cv_map.*_heading in profile.yaml (see: cvbuild.py --map).")

    head = [i for i, t in enumerate(texts) if t]
    out = {
        'name': idx.get('name', head[0]),
        'title': idx.get('title', head[1]),
        'contact': idx.get('contact', head[2]),
        'summary_heading': find(m['summary_heading']),
        'skills_heading': find(m['skills_heading']),
        'experience_heading': find(m['experience_heading']),
    }
    out['summary'] = idx.get('summary', out['summary_heading'] + 1)
    out['skills'] = [i for i in range(out['skills_heading'] + 1, out['experience_heading']) if texts[i]]
    return out


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
        assert len(skills) <= len(slots), f'max {len(slots)} skills lines in the base CV'
        for i, (lab, val) in enumerate(skills):
            p = P[slots[i]]
            p.runs[0].text = lab + ': '
            p.runs[1].text = val
            for r in p.runs[2:]:
                r.text = ''
        for j in range(len(skills), len(slots)):         # unused skill lines are removed
            P[slots[j]]._p.getparent().remove(P[slots[j]]._p)
    for e in c.get('edits', []):
        p = P[e['p']]
        if 'text' in e:
            settext(p, e['text'])
        elif 'replace' in e:
            old, new = e['replace']
            assert old in p.text, f"edit p{e['p']}: '{old[:40]}' not found in base paragraph"
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
    _check_text(prof, c.get('title', ''), c.get('summary', ''), *[v for _, v in c.get('skills', [])],
                *[e.get('text', '') + e.get('append', '') for e in c.get('edits', [])])
    name = c.get('file_name') or prof.output_stem(company_slug(folder), 'CV')
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
        # rc 2 = no text extractor (Poppler) installed: not a verdict, so judge by page count alone
        good = pages <= max_pages and (rc == 2 or 'layout: clean' in lay)
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
    _check_text(prof, body, L.get('re', ''), headline)
    if 'max_chars' in L:
        assert len(body) < L['max_chars'], f"letter body {len(body)} chars >= max_chars {L['max_chars']}"
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
    out = os.path.join(out_dir, (L.get('file_name') or prof.output_stem(company_slug(folder), 'Cover-Letter')) + '.docx')
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
    ok = r.returncode == 0 and res['layout_rc'] in (0, 2)
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
