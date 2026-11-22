"""Regenerates tests/fixtures/demo/demo_cv.docx, a fully fictional base CV. Run: python3 tests/fixtures/make_demo_cv.py"""
from pathlib import Path

import docx

OUT = Path(__file__).resolve().parent / "demo" / "demo_cv.docx"

d = docx.Document()
cp = d.core_properties
cp.author = "Example Author"
cp.last_modified_by = "Example Author"
cp.title = "Demo CV (fictional)"
cp.comments = "Fictional fixture for tests"

for t in ["ALEX EXAMPLE", "Senior Backend Engineer", "alex@example.com | Example City"]:
    d.add_paragraph(t)
d.add_paragraph("PROFESSIONAL SUMMARY")
d.add_paragraph("Backend engineer with a fictional career building services in Go and PostgreSQL.")
d.add_paragraph("TECHNICAL SKILLS")
for lab, val in [("Languages", "Go, Python"), ("Data", "PostgreSQL, Kafka"), ("Infrastructure", "Kubernetes, Terraform")]:
    p = d.add_paragraph()
    p.add_run(lab + ": ").bold = True
    p.add_run(val)
d.add_paragraph("PROFESSIONAL EXPERIENCE")
d.add_paragraph("Fictional Corp - Senior Backend Engineer - March 2021 - June 2024")
d.add_paragraph("Key Contributions:")
d.add_paragraph("Designed an invented billing API that handled a made-up 2,000 requests per second.")
d.add_paragraph("Mentored two fictional engineers.")
OUT.parent.mkdir(parents=True, exist_ok=True)
d.save(OUT)
print("wrote", OUT)
