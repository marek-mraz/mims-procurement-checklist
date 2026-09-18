#!/usr/bin/env python3
"""Native Word build of the booklet from the same JSON content as the Typst PDFs.
Real headings, tables, shaded panels, hyperlinks — clean to read AND to edit.
Run with tools/venv/bin/python (needs python-docx; pymupdf optional for cover)."""
import json, os, re

import content

# edition number and build date, set by build.sh (same stamp as in the PDF)
STAMP = ("DRAFT · " if os.environ.get("BOOKLET_VERSION", "dev").endswith("dev") else "") + \
    "v" + os.environ.get("BOOKLET_VERSION", "dev") + \
    (" · " + os.environ["BOOKLET_DATE"] if os.environ.get("BOOKLET_DATE") else "")

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))

EU = RGBColor(0x00, 0x33, 0x99)
MAG = RGBColor(0xC2, 0x18, 0x6F)
GRAY = RGBColor(0x5A, 0x5A, 0x6E)
DARKRED = RGBColor(0xA0, 0x20, 0x20)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
WARM = "FAF6EE"
BLUETINT = "EDF1FA"
REDTINT = "FBEEEE"
EUHEX = "003399"

def load(name):
    with open(os.path.join(HERE, "content", name), encoding="utf-8") as f:
        return json.load(f)

def languages():
    return sorted(f[:-5] for f in os.listdir(os.path.join(HERE, "content"))
                  if re.fullmatch(r"[a-z]{2}\.json", f))

def shade(cell, hexcolor):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hexcolor)
    tc_pr.append(shd)

def run(p, text, size=10, color=None, bold=False, italic=False):
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    if color is not None:
        r.font.color.rgb = color
    return r

def para(doc, text=None, size=10, color=None, bold=False, italic=False,
         before=2, after=4, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    if align is not None:
        p.alignment = align
    if text is not None:
        run(p, text, size=size, color=color, bold=bold, italic=italic)
    return p

def hyperlink(p, url, text, size=9):
    r_id = p.part.relate_to(
        url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True)
    hl = OxmlElement("w:hyperlink")
    hl.set(qn("r:id"), r_id)
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    c = OxmlElement("w:color"); c.set(qn("w:val"), EUHEX)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single")
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(size * 2))
    rpr.extend([c, u, sz])
    r.append(rpr)
    t = OxmlElement("w:t"); t.text = text
    r.append(t)
    hl.append(r)
    p._p.append(hl)

def heading(doc, text, size=18, color=EU, after=8, pagebreak_before=False):
    if pagebreak_before:
        doc.add_page_break()
    return para(doc, text, size=size, color=color, bold=True, before=6, after=after)

def panel_table(doc, cols=1):
    t = doc.add_table(rows=1, cols=cols)
    t.autofit = True
    return t

def cell_para(cell, first=False):
    p = cell.paragraphs[0] if first and not cell.paragraphs[0].runs else cell.add_paragraph()
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(3)
    return p

def bullet_lines(cell, lines, color=None, size=9, first=False):
    for i, line in enumerate(lines):
        p = cell_para(cell, first=first and i == 0)
        run(p, "•  ", size=size, color=color, bold=True)
        run(p, line, size=size)

def footer(doc, text):
    p = doc.sections[0].footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = run(p, text + "  ·  ", size=8, color=GRAY)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    p._p.append(fld)

def build(lang):
    L = content.load(lang)
    Q, U = L["quotes"], L["urls"]

    doc = Document()
    doc.core_properties.author = "Marek Mráz"
    st = doc.styles["Normal"]
    st.font.name = "Inter"
    st.font.size = Pt(10)
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(1.9)
        s.left_margin = s.right_margin = Cm(2.0)
    title = L["cover"]["title"].replace(" · ", " ")      # " · " marks the line breaks of the PDF cover
    footer(doc, f"{title} · MIMs Plus 9.0 · {STAMP}")

    # ---- cover ----
    for _ in range(6):
        para(doc, "")
    para(doc, title, size=26, color=EU, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
    para(doc, L["cover"]["subtitle"], size=15, color=MAG, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=16)
    para(doc, L["cover"]["tagline"], size=11, color=GRAY,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
    para(doc, L["cover"]["footer"], size=9, color=GRAY,
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, L["back"]["author"], size=8.5, color=GRAY, align=WD_ALIGN_PARAGRAPH.CENTER)

    # ---- why ----
    heading(doc, L["why"]["title"], pagebreak_before=True)
    for t in L["why"]["paras"]:
        para(doc, t, size=10.5, after=8)
    qt = panel_table(doc)
    cell = qt.rows[0].cells[0]
    shade(cell, BLUETINT)
    p = cell_para(cell, first=True)
    run(p, "“" + L["why"]["quote"]["text"].replace(" · ", "\n") + "”", size=10, italic=True)
    pol = L["why"]["policy"]
    para(doc, pol["title"], size=11, color=EU, bold=True, before=12, after=3)
    pt = panel_table(doc)
    cell = pt.rows[0].cells[0]
    shade(cell, WARM)
    p = cell_para(cell, first=True)
    run(p, pol["intro"], size=9.5)
    for law in pol["items"]:
        p = cell_para(cell)
        run(p, law["name"], size=9.5, color=EU, bold=True)
        run(p, f" ({law['ref']}): ", size=8.5, color=GRAY)
        run(p, law["text"], size=9.5)
    p = cell_para(cell)
    run(p, pol["note"], size=8.5, color=GRAY, italic=True)

    # ---- how to ----
    heading(doc, L["howto"]["title"], pagebreak_before=True)
    for i, s in enumerate(L["howto"]["steps"], 1):
        p = para(doc, after=6)
        run(p, f"{i}. {s['name']}  ", size=11, color=EU, bold=True)
        run(p, s["text"], size=10)
    para(doc, L["howto"]["legend_title"], size=11, color=MAG, bold=True, before=10)
    lt = panel_table(doc)
    cell = lt.rows[0].cells[0]
    shade(cell, WARM)
    from docx.enum.text import WD_COLOR_INDEX
    for i, e in enumerate(L["howto"]["legend"]):
        p = cell_para(cell, first=i == 0)
        run(p, "•  ", size=9.5, color=EU, bold=True)
        r = run(p, e["term"], size=9.5, color=EU, bold=True)
        r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        run(p, "  " + e["text"], size=9.5)
    p = cell_para(cell)
    run(p, L["howto"]["legend_note"], size=9.5)
    para(doc, L["howto"]["note"], size=9, color=GRAY, italic=True, before=8)

    # ---- glance ----
    heading(doc, L["glance"]["title"], pagebreak_before=True)
    para(doc, L["glance"]["intro"], size=10.5, after=10)
    for m in L["glance"]["items"]:
        p = para(doc, after=1)
        run(p, m["id"] + "  ", size=10, color=EU, bold=True)
        run(p, m["name"], size=10, bold=True)
        p = para(doc, after=1)
        run(p, m["q"] + "  ", size=9.5, color=MAG, bold=True)
        run(p, m["d"], size=9.5)
        p = para(doc, after=8)
        hyperlink(p, U[m["id"]], U[m["id"]].replace("https://", ""), size=8.5)
    para(doc, L["glance"]["tools_title"], size=11, color=EU, bold=True, before=6)
    for t in L["glance"]["tools"].values():
        p = para(doc, after=1)
        run(p, t["name"], size=10, color=EU, bold=True)
        p = para(doc, after=6)
        run(p, t["q"] + "  ", size=9.5, color=MAG, bold=True)
        run(p, t["d"], size=9.5)
    para(doc, L["glance"]["numbering_note"], size=9, color=GRAY, italic=True, before=4)

    # ---- MIM sections ----
    for m in L["mims"]:
        heading(doc, f"{m['id']} · {m['question']}", pagebreak_before=True, after=2)
        p = para(doc, after=2)
        run(p, m["name"] + "   ", size=10, color=GRAY)
        hyperlink(p, U[m["id"]], U[m["id"]].replace("https://", ""), size=8.5)
        para(doc, m["intro"], size=10, before=6, after=10)

        for i, it in enumerate(m["items"], 1):
            if it.get("label"):
                para(doc, it["label"].upper(), size=8, color=MAG, bold=True, after=0)
            p = para(doc, after=1)
            run(p, "☐  ", size=11, color=EU, bold=True)
            run(p, f"{m['id'][3:]}.{i}  ", size=10, color=EU, bold=True)
            run(p, it["text"], size=10, bold=True)
            p = para(doc, after=7)
            run(p, it["why"] + "   ", size=9, color=GRAY, italic=True)
            run(p, "→ " + it["refs"], size=8, color=MAG)

        pt = doc.add_table(rows=1, cols=2)
        pt.autofit = True
        c1, c2 = pt.rows[0].cells
        shade(c1, BLUETINT); shade(c2, REDTINT)
        p = cell_para(c1, first=True)
        run(p, L["why_title"].upper(), size=9, color=EU, bold=True)
        bullet_lines(c1, m["why_panel"], color=EU)
        p = cell_para(c2, first=True)
        run(p, L["flags_title"].upper(), size=9, color=DARKRED, bold=True)
        bullet_lines(c2, m["red_flags"], color=DARKRED)

        # spec quotes
        para(doc, L["spec_title"], size=13, color=EU, bold=True, before=14, after=2)
        para(doc, L["spec_leadin"], size=9, color=GRAY, after=6)
        two = lang != "en"
        st = doc.add_table(rows=0, cols=3 if two else 2)
        st.style = "Table Grid"
        ctr, qtr = L.get("capability_translations", {}), L.get("quote_translations", {})
        for c in Q[m["id"]]:
            rows = [(True, c["cap"], c["title"], ctr.get(c["cap"]))]
            rows += [(False, q["id"], q["en"], qtr.get(q["id"])) for q in c["quotes"]]
            for cap, rid, en, tr in rows:
                cells = st.add_row().cells
                rid = "" if cap and c.get("sub") else rid      # a heading inside a capability has no code
                texts = [rid.split(" · ")[-1]] + [t.replace(" · ", "\n") for t in ([tr or en, en] if two else [en])]
                for i, (cell, txt) in enumerate(zip(cells, texts)):
                    if cap:
                        shade(cell, BLUETINT)
                    run(cell.paragraphs[0], txt, size=8, bold=cap or i == 0,
                        color=EU if cap else MAG if i == 0 else GRAY if i == 2 else None)
        for row in st.rows:
            row.cells[0].width = Cm(1.4)
            for cell in row.cells[1:]:
                cell.width = Cm(15.6 / (len(row.cells) - 1))

        p = para(doc, before=8, after=2)
        run(p, L["spec_link_label"] + " ", size=9, color=GRAY)
        hyperlink(p, U[m["id"]], U[m["id"]], size=9)

    # ---- cross-cutting ----
    heading(doc, L["cross"]["title"], pagebreak_before=True, after=2)
    para(doc, L["cross"]["subtitle"], size=11, color=MAG, bold=True, after=6)
    para(doc, L["cross"]["intro"], size=10, after=10)
    for i, c in enumerate(L["cross"]["items"], 1):
        p = para(doc, after=1)
        run(p, "☐  ", size=11, color=EU, bold=True)
        run(p, f"X.{i}  {c['name']}", size=10.5, color=EU, bold=True)
        para(doc, c["text"], size=10, after=8)

    # ---- tick sheet ----
    # ---- worked example ----
    ex = L["example"]
    heading(doc, ex["title"], pagebreak_before=True)
    para(doc, ex["scenario"], size=10, after=8)
    para(doc, ex["table_title"], size=11, color=EU, bold=True, after=4)
    et = doc.add_table(rows=1, cols=3)
    et.style = "Table Grid"
    for c, htxt in zip(et.rows[0].cells, ex["table_headers"]):
        shade(c, BLUETINT)
        run(c.paragraphs[0], htxt, size=9, color=EU, bold=True)
    for r in ex["table_rows"]:
        cells = et.add_row().cells
        run(cells[0].paragraphs[0], r[0], size=9, color=EU, bold=True)
        run(cells[1].paragraphs[0], r[1], size=8.5, color=GRAY)
        run(cells[2].paragraphs[0], r[2], size=9)
    para(doc, ex["sample_title"], size=11, color=EU, bold=True, before=10, after=4)
    for i, line in enumerate(ex["sample"]):
        para(doc, line, size=9.5, bold=i == 0, after=3)
    para(doc, ex["tip"], size=9, color=GRAY, italic=True, before=6)
    para(doc, ex["filled_title"], size=11, color=EU, bold=True, before=8)
    ft = doc.add_table(rows=1, cols=5)
    ft.style = "Table Grid"
    for i, h in enumerate(L["tearout"]["headers"][j] for j in (0, 1, 4, 5, 6)):
        shade(ft.rows[0].cells[i], BLUETINT)
        run(ft.rows[0].cells[i].paragraphs[0], h, size=8.5, color=EU, bold=True)
    for r in ex["filled_rows"]:
        for cell, txt in zip(ft.add_row().cells, r):
            run(cell.paragraphs[0], txt, size=8.5)
    para(doc, ex["filled_note"], size=9, color=GRAY, italic=True, before=4)
    para(doc, ex["note"], size=9, color=GRAY, italic=True)

    heading(doc, L["tearout"]["title"], pagebreak_before=True)
    para(doc, L["tearout"]["intro"], size=9.5, after=4)
    para(doc, L["tearout"]["intro2"], size=9.5, after=8)
    ts = doc.add_table(rows=1, cols=7)
    ts.style = "Table Grid"
    widths = [Cm(1.0), Cm(4.6), Cm(3.0), Cm(1.9), Cm(1.4), Cm(3.8), Cm(1.4)]
    for i, htxt in enumerate(L["tearout"]["headers"]):
        cell = ts.rows[0].cells[i]
        cell.width = widths[i]
        shade(cell, BLUETINT)
        run(cell.paragraphs[0], htxt, size=8.5, color=EU, bold=True)
        if i >= 3:                        # who fills the column in
            run(cell.add_paragraph(), L["tearout"]["header_roles"][i - 3], size=7.5, color=GRAY, italic=True)

    def section_row(label):
        row = ts.add_row()
        merged = row.cells[0].merge(row.cells[6])
        shade(merged, EUHEX)
        run(merged.paragraphs[0], label, size=8.5, color=WHITE, bold=True)

    def item_row(num, short, ref):
        row = ts.add_row().cells
        for i, w in enumerate(widths):
            row[i].width = w
        run(row[0].paragraphs[0], num, size=8.5)
        run(row[1].paragraphs[0], short, size=8.5)
        run(row[2].paragraphs[0], ref, size=8, color=GRAY)
        run(row[3].paragraphs[0], "☐", size=10, color=EU)

    for m in L["mims"]:
        section_row(f"{m['id']} · {m['question']}")
        for i, short in enumerate(L["tearout_short"][m["id"]]):
            item_row(f"{m['id'][3:]}.{i+1}", short, m["items"][i]["refs"].replace(m["id"] + " ", ""))
    section_row(L["cross"]["title"] + "   " + L["tearout"]["cross_note"])
    for i, short in enumerate(L["tearout_short"]["CROSS"]):
        item_row(f"X.{i+1}", short, "—")
    para(doc, L["tearout"]["note"], size=8.5, color=GRAY, italic=True, before=8)
    if L["sheet_url"]:
        para(doc, L["tearout"]["download_label"] + " " + L["sheet_url"], size=8.5, color=GRAY)

    # ---- glossary ----
    heading(doc, L["glossary"]["title"], pagebreak_before=True)
    for t in L["glossary"]["terms"]:
        p = para(doc, after=6)
        run(p, t["t"] + "  —  ", size=10, color=EU, bold=True)
        run(p, t["d"], size=10)
    para(doc, L["glossary"]["more_title"], size=12, color=MAG, bold=True, before=12, after=6)
    for l in L["glossary"]["links"]:
        p = para(doc, after=5)
        hyperlink(p, "https://" + l["name"].split(" ")[0], l["name"], size=10)
        run(p, "  —  " + l["d"], size=10)

    # ---- back ----
    doc.add_page_break()
    para(doc, L["back"]["text"], size=9, color=GRAY, align=WD_ALIGN_PARAGRAPH.CENTER, before=24)
    para(doc, L["back"]["credits"], size=9, color=MAG, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, L["back"]["author"], size=8.5, color=GRAY, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, STAMP, size=8.5, color=GRAY, align=WD_ALIGN_PARAGRAPH.CENTER)

    out = os.path.join(os.path.dirname(HERE), f"MIMs-{os.environ.get('BOOKLET_NAME', 'draft')}-{lang}.docx")
    doc.save(out)
    print("wrote", out)

if __name__ == "__main__":
    for lang in languages():
        build(lang)
