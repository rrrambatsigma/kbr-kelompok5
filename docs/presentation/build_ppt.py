from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "PRESENTASI_KBR.pptx"

W = 13.333
H = 7.5

INK = RGBColor(0x1F, 0x3D, 0x2B)
SAGE = RGBColor(0x6F, 0x8F, 0x6A)
CREAM = RGBColor(0xFF, 0xFD, 0xF7)
BG = RGBColor(0xF7, 0xF2, 0xE7)
LIGHT = RGBColor(0xDC, 0xE8, 0xD5)
GOLD = RGBColor(0xB7, 0x79, 0x1F)
RED = RGBColor(0xA3, 0x3A, 0x2B)
GREEN = RGBColor(0x2F, 0x6B, 0x45)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x5B, 0x6B, 0x5E)
LINE = RGBColor(0xC9, 0xD6, 0xC1)

FONT = "Segoe UI"
FONT_BOLD = "Segoe UI Semibold"
CODE = "Consolas"


def add_rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(0.75)
    try:
        shp.shadow.inherit = False
    except Exception:
        pass
    return shp


def style_paragraph(p, size, color, bold=False, italic=False, font=FONT, align=None, line_spacing=1.0, space_after=0):
    if align is not None:
        p.alignment = align
    p.line_spacing = line_spacing
    p.space_after = Pt(space_after)
    for run in p.runs:
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color


def add_text(slide, text, x, y, w, h, size=14, color=INK, bold=False, italic=False, font=FONT,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.0,
             margins=(0.04, 0.04, 0.02, 0.02)):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = Inches(margins[0])
    tf.margin_right = Inches(margins[1])
    tf.margin_top = Inches(margins[2])
    tf.margin_bottom = Inches(margins[3])
    tf.vertical_anchor = anchor
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    style_paragraph(p, size, color, bold=bold, italic=italic, font=font, align=align, line_spacing=line_spacing)
    return tb


def add_bullets(slide, items, x, y, w, h, size=13, color=INK, spacing=5, font=FONT, line_spacing=1.0):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    tf.clear()
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {item}"
        style_paragraph(p, size, color, font=font, line_spacing=line_spacing, space_after=spacing)
    return tb


def add_pill(slide, text, x, y, w, h, fill=LIGHT, color=INK, size=9.5):
    shp = add_rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.06)
    tf.margin_right = Inches(0.06)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    style_paragraph(p, size, color, bold=True, font=FONT_BOLD, align=PP_ALIGN.CENTER)
    return shp


def add_title(slide, kicker, title, subtitle=None):
    add_rect(slide, 0, 0, W, 0.07, INK)
    add_text(slide, kicker.upper(), 0.65, 0.26, 11.8, 0.28, size=9.5, color=SAGE, bold=True)
    add_text(slide, title, 0.65, 0.56, 12.0, 0.64, size=27, color=INK, bold=True)
    add_rect(slide, 0.65, 1.23, 1.15, 0.045, SAGE)
    if subtitle:
        add_text(slide, subtitle, 0.65, 1.36, 11.9, 0.35, size=11.5, color=MUTED)


def add_footer(slide, num, total=12):
    add_rect(slide, 0.65, 7.12, 12.03, 0.012, LINE)
    add_text(slide, "KBR Kelompok 5 · 2026", 0.65, 7.18, 7.0, 0.22, size=8.5, color=MUTED)
    add_text(slide, f"{num:02d} / {total:02d}", 11.5, 7.18, 1.18, 0.22, size=8.5, color=MUTED, align=PP_ALIGN.RIGHT)


def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def new_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(slide, 0, 0, W, H, BG)
    return slide


def add_table(slide, rows, x, y, w, h, col_widths, row_heights=None, font_size=10,
              header_size=10, header_fill=INK, header_color=WHITE, body_fill=WHITE,
              alt_fill=CREAM, first_col_bold=False, cell_colors=None, center_cols=()):
    row_count = len(rows)
    col_count = len(rows[0])
    shape = slide.shapes.add_table(row_count, col_count, Inches(x), Inches(y), Inches(w), Inches(h))
    table = shape.table
    table.first_row = True
    table.horz_banding = False
    for i, cw in enumerate(col_widths):
        table.columns[i].width = Inches(cw)
    if row_heights:
        for i, rh in enumerate(row_heights):
            table.rows[i].height = Inches(rh)
    else:
        for r in range(row_count):
            table.rows[r].height = Inches(h / row_count)
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            cell = table.cell(r, c)
            cell.margin_left = Inches(0.06)
            cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = header_fill
            else:
                cell.fill.fore_color.rgb = body_fill if r % 2 == 1 else alt_fill
            tf = cell.text_frame
            tf.word_wrap = True
            tf.clear()
            p = tf.paragraphs[0]
            p.text = str(text)
            align = PP_ALIGN.CENTER if r == 0 or c in center_cols else PP_ALIGN.LEFT
            style_paragraph(p, header_size if r == 0 else font_size, header_color if r == 0 else INK,
                            bold=(r == 0) or (first_col_bold and c == 0), font=FONT, align=align)
            if cell_colors and r < len(cell_colors) and c < len(cell_colors[r]) and cell_colors[r][c] is not None:
                for run in p.runs:
                    run.font.color.rgb = cell_colors[r][c]
    return table


def add_stat_card(slide, value, label, x, y, w, h, accent=SAGE):
    add_rect(slide, x, y, w, h, WHITE, line=LINE)
    add_rect(slide, x, y, 0.08, h, accent, line=None)
    add_text(slide, value, x + 0.18, y + 0.12, w - 0.3, 0.55, size=27, color=INK, bold=True)
    add_text(slide, label, x + 0.18, y + 0.78, w - 0.3, 0.45, size=9.5, color=MUTED)


def add_flow_block(slide, num, title, sub, x, y, w, h, fill=WHITE, color=INK, sub_color=MUTED, accent=SAGE):
    add_rect(slide, x, y, w, h, fill, line=LINE)
    add_rect(slide, x, y, w, 0.06, accent, line=None)
    add_text(slide, num, x + 0.12, y + 0.13, 0.5, 0.28, size=8.5, color=accent, bold=True)
    add_text(slide, title, x + 0.12, y + 0.43, w - 0.24, 0.54, size=11.2, color=color, bold=True)
    add_text(slide, sub, x + 0.12, y + 1.02, w - 0.24, h - 1.1, size=8.6, color=sub_color, line_spacing=1.05)


def add_arrow(slide, x, y, w=0.22, h=0.22, color=SAGE):
    add_rect(slide, x, y, w, h, color, line=None, shape=MSO_SHAPE.RIGHT_ARROW)


def add_bar(slide, label, value, max_value, x, y, max_w, color=INK):
    add_text(slide, label, x, y - 0.03, 2.1, 0.3, size=9.3, color=INK)
    bar_x = x + 2.15
    add_rect(slide, bar_x, y + 0.04, max_w, 0.26, LIGHT, line=None)
    if value > 0:
        add_rect(slide, bar_x, y + 0.04, max_w * (value / max_value), 0.26, color, line=None)
    add_text(slide, str(value), bar_x + max_w + 0.1, y - 0.02, 0.55, 0.3, size=9.3, color=color, bold=True)


def add_dl_card(slide, letter, title, example, x, y, w, h, fill=WHITE, accent=SAGE):
    add_rect(slide, x, y, w, h, fill, line=LINE)
    add_rect(slide, x, y, 0.08, h, accent, line=None)
    add_text(slide, letter, x + 0.2, y + 0.1, 0.65, 0.55, size=28, color=INK, bold=True)
    add_text(slide, title, x + 0.85, y + 0.2, w - 1.0, 0.28, size=9.5, color=MUTED, bold=True)
    add_text(slide, example, x + 0.2, y + 0.82, w - 0.4, h - 0.92, size=10.2, color=INK, line_spacing=1.12)


def add_roadmap_card(slide, num, title, sub, x, y, w, h):
    add_rect(slide, x, y, w, h, WHITE, line=LINE)
    add_text(slide, num, x + 0.2, y + 0.12, 0.7, 0.45, size=24, color=SAGE, bold=True)
    add_text(slide, title, x + 0.2, y + 0.68, w - 0.4, 0.55, size=12, color=INK, bold=True)
    add_text(slide, sub, x + 0.2, y + 1.25, w - 0.4, h - 1.35, size=9.5, color=MUTED, line_spacing=1.12)


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    prs.core_properties.title = "KBR — Sistem Pakar Penyakit Tanaman Pangan"
    prs.core_properties.author = "KBR Kelompok 5"
    prs.core_properties.subject = "Materi presentasi progres knowledge base dan expert system"

    s = new_slide(prs)
    add_rect(s, 0, 0, 4.55, H, INK)
    add_rect(s, 4.55, 0, 0.08, H, SAGE)
    add_text(s, "KBR · KELOMPOK 5", 0.55, 0.55, 3.4, 0.3, size=10, color=LIGHT, bold=True)
    add_text(s, "Knowledge Base\n& Expert System", 0.55, 1.05, 3.5, 1.6, size=28, color=CREAM, bold=True, line_spacing=1.0)
    add_text(s, "Penyakit tanaman pangan tropis", 0.55, 2.95, 3.4, 0.6, size=12, color=LIGHT)
    add_rect(s, 0.55, 3.85, 1.2, 0.045, SAGE)
    add_text(s, "Mata kuliah Basis Pengetahuan\ndan Penalaran · 2026", 0.55, 4.15, 3.4, 0.7, size=10, color=LIGHT, line_spacing=1.15)
    add_text(s, "Kelompok 5", 0.55, 6.55, 3.4, 0.3, size=11, color=CREAM, bold=True)
    add_text(s, "PROGRES PROYEK · 2026", 5.15, 0.85, 7.0, 0.3, size=10, color=SAGE, bold=True)
    add_text(s, "Dari sumber verbatim ke\nontologi OWL 2 dan reasoning", 5.15, 1.35, 7.5, 1.6, size=34, color=INK, bold=True, line_spacing=0.98)
    add_text(s, "Knowledge base dan prototipe expert system untuk diagnosis awal penyakit pada tujuh tanaman pangan.", 5.15, 3.2, 7.0, 0.8, size=14, color=MUTED, line_spacing=1.15)
    add_pill(s, "7 tanaman", 5.15, 4.45, 1.75, 0.42, fill=LIGHT, color=INK, size=10)
    add_pill(s, "53 penyakit", 7.05, 4.45, 1.8, 0.42, fill=LIGHT, color=INK, size=10)
    add_pill(s, "OWL 2 + SWRL", 9.0, 4.45, 1.95, 0.42, fill=INK, color=WHITE, size=10)
    add_text(s, "16.812 triple kanonik   ·   1.205 individu   ·   87 kelas", 5.15, 5.45, 7.4, 0.35, size=11, color=INK, bold=True)
    add_text(s, "Sumber: DOC002–DOC005 + 45 sumber eksternal", 5.15, 5.85, 7.4, 0.35, size=10, color=MUTED)
    add_text(s, "Kelompok 5 · 2026", 5.15, 6.65, 7.0, 0.3, size=9, color=MUTED)
    add_notes(s, "Perkenalkan proyek, tujuh tanaman, 53 penyakit, dan fokus pada knowledge base yang bisa di-reasoning serta ditelusuri buktinya.")

    s = new_slide(prs)
    add_title(s, "01 · LATAR BELAKANG", "Pengetahuan tersebar, tetapi harus bisa ditelusuri",
              "Ruang lingkup: tujuh tanaman pangan tropis; diagnosis awal, bukan kepastian laboratorium.")
    add_stat_card(s, "7", "Tanaman pangan tropis", 0.65, 1.82, 3.0, 1.2, accent=SAGE)
    add_stat_card(s, "53", "Penyakit dalam cakupan", 3.9, 1.82, 3.0, 1.2, accent=INK)
    add_stat_card(s, "78", "Tautan penyakit–patogen", 7.15, 1.82, 3.0, 1.2, accent=GOLD)
    add_stat_card(s, "6", "Blok pipeline utama", 10.4, 1.82, 2.28, 1.2, accent=SAGE)
    add_text(s, "MASALAH", 0.65, 3.38, 2.0, 0.28, size=9.5, color=SAGE, bold=True)
    problem_blocks = [
        ("Pengetahuan tersebar", "buku, tabel, sumber eksternal"),
        ("Sulit ditelusuri", "tidak ada offset & kutipan"),
        ("Sulit di-reasoning", "relasi tidak eksplisit"),
        ("Sulit dipakai", "belum ada API diagnosis"),
    ]
    for i, (title, sub) in enumerate(problem_blocks):
        x = 0.65 + i * 3.08
        add_rect(s, x, 3.72, 2.82, 1.05, WHITE, line=LINE)
        add_text(s, title, x + 0.16, 3.86, 2.5, 0.32, size=11, color=INK, bold=True)
        add_text(s, sub, x + 0.16, 4.2, 2.5, 0.35, size=9.2, color=MUTED)
        if i < 3:
            add_arrow(s, x + 2.86, 4.1, 0.18, 0.18, color=SAGE)
    add_rect(s, 0.65, 5.15, 12.03, 1.45, CREAM, line=LINE)
    add_text(s, "RUANG LINGKUP", 0.85, 5.3, 2.2, 0.28, size=9.5, color=GOLD, bold=True)
    add_bullets(s, [
        "Tujuh tanaman: padi, kedelai, jagung, ubi jalar, ubi kayu, kacang tanah, kacang hijau.",
        "53 penyakit; 78 tautan penyakit–patogen; tanaman di luar cakupan tidak dibuat sebagai individu.",
        "Luaran: diagnosis awal, bukan kepastian laboratorium.",
    ], 0.85, 5.6, 11.5, 0.9, size=10.5, spacing=2)
    add_footer(s, 2)
    add_notes(s, "Jelaskan masalah utama: pengetahuan tersebar dan sulit ditelusuri. Tegaskan ruang lingkup tujuh tanaman dan batas diagnosis awal.")

    s = new_slide(prs)
    add_title(s, "02 · PIPELINE", "Dari sumber verbatim ke expert system",
              "Deterministik, verbatim, dan dapat diaudit.")
    add_pill(s, "deterministik · verbatim · traceable", 8.75, 1.52, 3.9, 0.38, fill=LIGHT, color=INK, size=9)
    blocks = [
        ("01", "Sumber", "DOC002–DOC005\n+ 45 sumber eksternal", LIGHT, INK, INK),
        ("02", "Ekstraksi", "LlamaParse\nhalaman · blok · chunk", WHITE, INK, MUTED),
        ("03", "Knowledge Tables", "auto → review → curated\nverbatim + offset", WHITE, INK, MUTED),
        ("04", "Ontologi", "TBox manual\nABox generated", INK, WHITE, LIGHT),
        ("05", "Reasoning", "Pellet\n7 aturan SWRL", SAGE, WHITE, LIGHT),
        ("06", "Expert System", "Spring Boot + Jena\nAPI tipis", WHITE, INK, MUTED),
    ]
    for i, (num, title, sub, fill, color, sub_color) in enumerate(blocks):
        x = 0.9 + i * 1.97
        add_flow_block(s, num, title, sub, x, 2.3, 1.65, 2.0, fill=fill, color=color, sub_color=sub_color)
        if i < 5:
            add_arrow(s, x + 1.69, 3.25, 0.2, 0.2, color=SAGE)
    add_text(s, "Tanpa LLM/RAG di dalam pipeline. Setiap baris menyimpan chunk_id, offset karakter, halaman, dan kutipan.",
             0.65, 4.7, 12.03, 0.45, size=12, color=INK)
    add_text(s, "Luaran teknis", 0.65, 5.4, 2.0, 0.3, size=9.5, color=SAGE, bold=True)
    add_pill(s, "ontology.ttl", 0.65, 5.72, 2.55, 0.42, fill=WHITE, color=INK, size=9.5)
    add_pill(s, "ontology_md.ttl", 3.38, 5.72, 2.55, 0.42, fill=WHITE, color=INK, size=9.5)
    add_pill(s, "API /api/diagnosis", 6.11, 5.72, 4.55, 0.42, fill=INK, color=WHITE, size=9.5)
    add_text(s, "SWRL dan enrichment ada di ontology_md.ttl; backend memuat ontology_md_inferred.ttl lewat Apache Jena.", 0.65, 6.35, 11.9, 0.35, size=9.5, color=MUTED)
    add_footer(s, 3)
    add_notes(s, "Jelaskan enam blok pipeline. Tekankan deterministik dan verbatim: tidak ada LLM/RAG; setiap baris punya chunk_id, offset, halaman, dan kutipan.")

    s = new_slide(prs)
    add_title(s, "03 · TBOX VS ABOX", "Skema dan data dipisahkan",
              "TBox mendefinisikan; ABox mengisi; reasoner menyimpulkan.")
    add_rect(s, 0.65, 1.7, 5.9, 0.5, INK, line=None)
    add_text(s, "TBOX — SKEMA", 0.85, 1.82, 5.4, 0.26, size=11, color=WHITE, bold=True)
    add_rect(s, 0.65, 2.2, 5.9, 1.95, WHITE, line=LINE)
    add_bullets(s, [
        "87 kelas · 32 object property · 34 data property",
        "Definisi, domain/range, disjointness",
        "Restriksi, property chain, nominal, inverse, cardinality",
        "File: tbox.py",
    ], 0.85, 2.36, 5.5, 1.65, size=10.5, spacing=4)
    add_rect(s, 6.78, 1.7, 5.9, 0.5, SAGE, line=None)
    add_text(s, "ABOX — FAKTA", 6.98, 1.82, 5.4, 0.26, size=11, color=WHITE, bold=True)
    add_rect(s, 6.78, 2.2, 5.9, 1.95, WHITE, line=LINE)
    add_bullets(s, [
        "1.205 individu · 16.812 triple",
        "7 tanaman · 53 penyakit · 78 tautan",
        "Fakta + bukti + provenance",
        "File: build_ontology.py / ontology.ttl",
    ], 6.98, 2.36, 5.5, 1.65, size=10.5, spacing=4)
    add_rect(s, 0.65, 4.45, 12.03, 2.05, CREAM, line=LINE)
    add_text(s, "CONTOH INFERENSI", 0.85, 4.58, 3.0, 0.28, size=9.5, color=GOLD, bold=True)
    add_text(s, "TBox   : PenyakitJamur ≡ Penyakit ⊓ ∃disebabkanOleh.Jamur\n"
                "ABox   : PenyakitBlasPadi disebabkanOleh MagnaportheOryzae\n"
                "Reason : PenyakitBlasPadi rdf:type PenyakitJamur\n"
                "Makna  : kategori tidak ditulis manual; reasoner menurunkannya.",
             0.85, 4.95, 11.4, 1.35, size=10.5, color=INK, font=CODE, line_spacing=1.25)
    add_footer(s, 4)
    add_notes(s, "Bandingkan TBox sebagai definisi dan ABox sebagai fakta. Gunakan contoh PenyakitBlasPadi untuk menunjukkan kategori PenyakitJamur muncul dari reasoning, bukan ditulis manual.")

    s = new_slide(prs)
    add_title(s, "04 · DL EXPRESSIVITY", "SROIQ(D): fitur logika yang dipakai",
              "OWL 2 DL setara SROIQ(D); Pellet/HermiT mendukung reasoning.")
    dl_cards = [
        ("S", "Peran transitif + hierarki", "bagianDari: Daun → Pucuk → Batang", LIGHT),
        ("R", "Property chain", "memilikiGejala ∘ terdapatPada\n⊑ menyerangBagian", WHITE),
        ("O", "Nominal", "Serealia ≡ {Padi, Jagung}\nLegum ≡ {Kedelai, KacangTanah, KacangHijau}", WHITE),
        ("I", "Inverse role", "menyerangTanaman ↔ diserangPenyakit\n8 pasang owl:inverseOf", WHITE),
        ("Q", "Qualified cardinality", "Penyakit ⊑ ≥1 memilikiReferensi.Referensi\nBuku ⊑ =1 tahunTerbit.xsd:integer", LIGHT),
        ("D", "Data range", "xsd:string · xsd:integer\nxsd:decimal · xsd:anyURI · rdf:PlainLiteral", WHITE),
    ]
    for i, (letter, title, example, fill) in enumerate(dl_cards):
        x = 0.65 + (i % 3) * 4.0
        y = 1.75 + (i // 3) * 2.25
        add_dl_card(s, letter, title, example, x, y, 3.7, 1.95, fill=fill)
    add_text(s, "Lebih ekspresif daripada OWL 2 EL/QL/RL · konsekuensi: reasoning lebih mahal, tetapi dataset masih wajar.",
             0.65, 6.25, 12.03, 0.35, size=10, color=MUTED)
    add_footer(s, 5)
    add_notes(s, "Jelaskan setiap huruf dengan contoh proyek. Fokus pada S transitive, R property chain, O nominal, I inverse, Q cardinality, dan D datatype. Hindari definisi formal yang terlalu panjang.")

    s = new_slide(prs)
    add_title(s, "05 · SWRL & REASONING", "Aturan if–then dan hasil inferensi",
              "Kandidat penyakit, rekomendasi pengendalian, dan klasifikasi kategori.")
    rows = [
        ["Aturan", "Jika", "Maka"],
        ["R1\nGejala", "Diagnosis punya tanaman + observasi gejala; penyakit menyerang tanaman itu dan punya gejala kanonik sama", "menghasilkan\nPenyakit"],
        ["R2\nLingkungan", "Diagnosis punya observasi lingkungan; penyakit dipengaruhi faktor lingkungan dengan klasifikasi sama", "menghasilkan\nPenyakit"],
        ["R3\nSpesifik", "Penyakit kandidat punya dikendalikanDengan aksi", "merekomendasikan\nPengendalian"],
        ["R4\nUmum", "Penyakit kandidat menyerang tanaman; tanaman punya pengendalianUmum", "merekomendasikan\nPengendalian"],
        ["R5\nKuat", "Dua gejala kanonik berbeda; kodeGejala dibandingkan dengan swrlb:notEqual", "kandidat\nKuat"],
        ["R6\nVarietas", "Penyakit kandidat punya varietas dengan tahanTerhadap", "merekomendasikan\nVarietas"],
        ["R7\nRisiko", "Kondisi lingkungan diagnosis cocok dengan dipengaruhiOleh penyakit", "menandai\nRisiko"],
    ]
    add_table(s, rows, 0.65, 1.7, 6.55, 4.27, [1.35, 3.65, 1.55],
              row_heights=[0.42, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55], font_size=8.2, header_size=9.2,
              first_col_bold=True)
    add_text(s, "Hasil inferensi Pellet", 7.45, 1.7, 4.0, 0.3, size=12, color=INK, bold=True)
    bars = [
        ("PenyakitJamur", 26, INK),
        ("PenyakitBakteri", 5, SAGE),
        ("PenyakitVirus", 5, SAGE),
        ("PenyakitOomycete", 1, GOLD),
        ("PenyakitFitoplasma", 1, GOLD),
        ("PenyakitNematoda", 0, RED),
    ]
    for i, (label, value, color) in enumerate(bars):
        add_bar(s, label, value, 26, 7.45, 2.22 + i * 0.55, 2.35, color=color)
    add_text(s, "50 demo · 162 penyakit · 608 pengendalian · 41 kandidat kuat · 175 varietas · 22 risiko",
             7.45, 5.55, 5.0, 0.45, size=9.2, color=INK, bold=True)
    add_text(s, "Pellet offline; Jena hanya membaca ontology_md_inferred.ttl.",
             0.65, 6.23, 12.03, 0.35, size=10.5, color=RED, bold=True)
    add_footer(s, 6)
    add_notes(s, "Jelaskan R1–R4 secara singkat. Tekankan hasil 26/5/5/1/1/0 adalah inferensi, bukan assertion manual. Sebut batas: SWRL belum dieksekusi Jena.")

    s = new_slide(prs)
    add_title(s, "06 · BUKTI & SKALA", "Angka besar, tetapi tetap bisa diaudit",
              "Setiap klaim dapat dilacak ke kutipan, halaman, chunk, dan offset.")
    add_stat_card(s, "16.812", "Triple kanonik", 0.65, 1.75, 2.85, 1.35, accent=INK)
    add_stat_card(s, "1.205", "Individu kanonik", 3.73, 1.75, 2.85, 1.35, accent=SAGE)
    add_stat_card(s, "19.326", "Triple enrichment", 6.81, 1.75, 2.85, 1.35, accent=GOLD)
    add_stat_card(s, "1.367", "Individu enrichment", 9.89, 1.75, 2.79, 1.35, accent=SAGE)
    chain = [
        ("PDF", "sumber"),
        ("Chunk", "teks"),
        ("Offset CSV", "char_start/end"),
        ("BuktiSumber", "783 node"),
        ("prov:wasDerivedFrom", "BukuDOC002/005"),
    ]
    for i, (title, sub) in enumerate(chain):
        x = 0.9 + i * 2.38
        add_rect(s, x, 3.55, 2.0, 1.2, WHITE, line=LINE)
        add_text(s, title, x + 0.15, 3.7, 1.7, 0.3, size=10.5, color=INK, bold=True)
        add_text(s, sub, x + 0.15, 4.08, 1.7, 0.35, size=8.8, color=MUTED)
        if i < 4:
            add_arrow(s, x + 2.04, 4.02, 0.2, 0.2, color=SAGE)
    add_pill(s, "783 node BuktiSumber", 0.65, 5.25, 3.3, 0.45, fill=LIGHT, color=INK, size=9.5)
    add_pill(s, "1.407 tautan didukungOleh", 4.13, 5.25, 3.55, 0.45, fill=LIGHT, color=INK, size=9.5)
    add_pill(s, "78 test ontology", 7.86, 5.25, 2.85, 0.45, fill=INK, color=WHITE, size=9.5)
    add_text(s, "Kanonik: 87 kelas · 32 OP · 34 DP · 53 penyakit · 78 tautan penyakit–patogen.",
             0.65, 6.0, 12.03, 0.35, size=11, color=INK, bold=True)
    add_text(s, "Enrichment menambah 2.514 triple, 942 fakta, dan 559 deskripsi rdfs:comment.",
             0.65, 6.38, 12.03, 0.35, size=9.5, color=MUTED)
    add_footer(s, 7)
    add_notes(s, "Tunjukkan skala data dan rantai bukti. Tekankan provenance: kutipan, halaman, chunk, offset, prov:wasDerivedFrom. Sebut 78 test ontology lulus.")

    s = new_slide(prs)
    add_title(s, "07 · STATUS & GAP", "Selesai, scaffold, dan yang belum",
              "Gap dilaporkan terbuka agar prioritas perbaikan jelas.")
    rows = [
        ["Bagian", "Status"],
        ["Knowledge tables + audit", "Selesai"],
        ["Ontologi OWL 2 + enrichment", "Selesai"],
        ["Reasoning Pellet + 7 SWRL", "Selesai"],
        ["Inferred graph + endpoint diagnosis", "Selesai"],
        ["Frontend", "Belum"],
    ]
    colors = [[None, None], [None, GREEN], [None, GREEN], [None, GREEN], [None, GREEN], [None, RED]]
    add_table(s, rows, 0.65, 1.7, 6.35, 3.9, [4.4, 1.95],
              row_heights=[0.42, 0.65, 0.65, 0.65, 0.65, 0.65], font_size=10, header_size=10,
              first_col_bold=True, cell_colors=colors, center_cols=(1,))
    add_rect(s, 7.25, 1.7, 5.43, 3.9, WHITE, line=LINE)
    add_text(s, "GAP YANG DILAPORKAN", 7.45, 1.85, 4.8, 0.28, size=9.5, color=RED, bold=True)
    add_bullets(s, [
        "51 gejala belum dipetakan ke kosakata kanonik",
        "37 baris pengendalian belum dipetakan",
        "210 kutipan masih berupa fragmen",
        "Tidak ada pH; observasi lingkungan numerik sparse",
        "17 penyakit ubi kayu memakai fallback pengendalianUmum",
        "Pellet offline; Jena hanya membaca inferred TTL",
    ], 7.45, 2.25, 4.95, 2.2, size=10.2, spacing=6)
    add_rect(s, 7.45, 4.55, 5.03, 0.72, LIGHT, line=None)
    add_text(s, "Prioritas: frontend, ranking, lengkapi mapping, tambah pH.", 7.62, 4.7, 4.7, 0.4, size=9.2, color=INK, bold=True)
    add_text(s, "Diagnosis awal, bukan kepastian laboratorium.", 0.65, 5.95, 12.03, 0.35, size=11, color=GOLD, bold=True)
    add_footer(s, 8)
    add_notes(s, "Sampaikan status apa adanya. Tiga bagian selesai, backend masih scaffold, endpoint diagnosis dan frontend belum. Sebut gap 58/37/210, pH, fallback ubi kayu, dan SWRL Jena.")

    s = new_slide(prs)
    add_title(s, "08 · RENCANA", "Dari prototipe ke diagnosis yang bisa dipakai",
              "Fokus terdekat: endpoint diagnosis dan ranking.")
    roadmap = [
        ("01", "Endpoint diagnosis", "Petakan gejala ke GejalaKanonik; ranking kandidat."),
        ("02", "Frontend", "Form gejala, hasil diagnosis, tampilan bukti."),
        ("03", "Perbaikan data", "Mapping 51 gejala + 37 kendali; tambah pH."),
        ("04", "Integrasi reasoning", "SWRL/SPARQL, provenance di API, evaluasi."),
    ]
    for i, (num, title, sub) in enumerate(roadmap):
        x = 0.65 + i * 3.13
        add_roadmap_card(s, num, title, sub, x, 1.75, 2.85, 2.3)
    add_rect(s, 0.65, 4.55, 12.03, 1.85, INK, line=None)
    add_text(s, "Terima kasih", 1.0, 4.78, 5.0, 0.65, size=30, color=CREAM, bold=True)
    add_text(s, "Q&A", 1.0, 5.6, 2.0, 0.35, size=16, color=LIGHT, bold=True)
    add_text(s, "KBR Kelompok 5 · 2026", 8.4, 4.95, 3.8, 0.3, size=11, color=LIGHT, align=PP_ALIGN.RIGHT)
    add_text(s, "Diagnosis awal, bukan kepastian laboratorium", 8.4, 5.35, 3.9, 0.3, size=9.5, color=LIGHT, align=PP_ALIGN.RIGHT)
    add_footer(s, 9)
    add_notes(s, "Tutup dengan rencana: endpoint diagnosis, frontend, perbaikan data, integrasi reasoning. Buka Q&A dan ingatkan batas diagnosis awal.")

    s = new_slide(prs)
    add_title(s, "BACKUP A · SROIQ(D)", "Detail aksioma dan implementasi",
              "Rujukan: 04_ontology/README.md dan tbox.py.")
    rows = [
        ["Huruf", "Aksioma", "Implementasi di proyek"],
        ["S", "Transitive role & role hierarchy", "bagianDari transitive (Daun → Pucuk → Batang); dikendalikanDengan, pengendalianUmum, merekomendasikanPengendalian ⊑ berkaitanPengendalian"],
        ["R", "Property chain", "memilikiGejala ∘ terdapatPada ⊑ menyerangBagian"],
        ["O", "Nominal", "Serealia ≡ {Padi, Jagung}; Legum ≡ {Kedelai, KacangTanah, KacangHijau}; UmbiUmbian ≡ {UbiKayu, UbiJalar}"],
        ["I", "Inverse", "8 pasang owl:inverseOf"],
        ["Q", "Qualified cardinality", "Penyakit ⊑ (memilikiReferensi min 1 Referensi); Buku ⊑ (tahunTerbit exactly 1 xsd:integer)"],
        ["D", "Data range", "xsd:string, xsd:integer, xsd:decimal, xsd:anyURI, rdf:PlainLiteral"],
    ]
    add_table(s, rows, 0.65, 1.7, 12.03, 4.6, [0.9, 4.4, 6.73],
              row_heights=[0.42, 0.72, 0.62, 0.86, 0.62, 0.72, 0.62], font_size=9.3, header_size=9.5,
              first_col_bold=True, center_cols=(0,))
    add_text(s, "Contoh inferensi: Daun bagianDari Batang; menyerangBagian; Serealia = {Padi, Jagung}.",
             0.65, 6.5, 12.03, 0.35, size=9.5, color=MUTED)
    add_footer(s, 10)
    add_notes(s, "Backup untuk pertanyaan detail SROIQ(D). Tunjukkan bahwa setiap fitur punya contoh nyata di tbox.py.")

    s = new_slide(prs)
    add_title(s, "BACKUP B · SWRL", "Tujuh aturan dan konsekuensinya",
              "Rujukan: 04_ontology/swrl_rules.ttl.")
    rows = [
        ["Aturan", "Body ringkas", "Head"],
        ["R1\nRuleKandidatGejala", "Diagnosis(d) · memilikiTanaman(d,t) · TanamanPangan(t) · memilikiObservasi(d,o) · memilikiGejalaKanonik(o,g) · menyerangTanaman(p,t) · memilikiGejala(p,gp) · memilikiGejalaKanonik(gp,g)", "menghasilkanPenyakit(d,p)"],
        ["R2\nRuleKandidatLingkungan", "Diagnosis(d) · memilikiTanaman(d,t) · memilikiObservasi(d,o) · ObservasiLingkungan(o) · klasifikasiTurunan(o,f) · dipengaruhiOleh(p,eo) · klasifikasiTurunan(eo,f) · menyerangTanaman(p,t)", "menghasilkanPenyakit(d,p)"],
        ["R3\nRuleRekomendasiSpesifik", "Diagnosis(d) · menghasilkanPenyakit(d,p) · dikendalikanDengan(p,c)", "merekomendasikanPengendalian(d,c)"],
        ["R4\nRuleRekomendasiUmum", "Diagnosis(d) · menghasilkanPenyakit(d,p) · menyerangTanaman(p,t) · pengendalianUmum(t,c)", "merekomendasikanPengendalian(d,c)"],
        ["R5\nRuleKandidatKuat", "Dua gejala kanonik berbeda; kodeGejala(?g,?gn) · kodeGejala(?g2,?gn2) · swrlb:notEqual(?gn,?gn2) · penyakit memiliki kedua gejala", "kandidatKuat(d,p)"],
        ["R6\nRuleRekomendasiVarietasTahan", "menghasilkanPenyakit(d,p) · menyerangTanaman(p,t) · memilikiVarietas(t,v) · tahanTerhadap(v,p)", "merekomendasikanVarietas(d,v)"],
        ["R7\nRuleRisikoLingkungan", "memilikiObservasi(d,o) · ObservasiLingkungan(o) · klasifikasiTurunan(o,f) · dipengaruhiOleh(p,eo) · klasifikasiTurunan(eo,f)", "menandaiRisikoLingkungan(d,p)"],
    ]
    add_table(s, rows, 0.65, 1.65, 12.03, 4.9, [1.6, 8.0, 2.43],
              row_heights=[0.36, 0.64, 0.64, 0.64, 0.64, 0.67, 0.67, 0.64], font_size=7.2, header_size=8.8,
              first_col_bold=True)
    add_text(s, "Pellet offline; Jena hanya membaca ontology_md_inferred.ttl.",
             0.65, 6.68, 12.03, 0.3, size=9.5, color=RED, bold=True)
    add_footer(s, 11)
    add_notes(s, "Backup untuk pertanyaan detail aturan. Jelaskan body dan head, lalu tegaskan SWRL dijalankan offline.")

    s = new_slide(prs)
    add_title(s, "BACKUP C · BUKTI & Q&A", "Rantai bukti dan pertanyaan yang sering muncul",
              "Gunakan slide ini jika waktu memungkinkan.")
    add_text(s, "RANTAI BUKTI", 0.65, 1.7, 3.0, 0.3, size=9.5, color=SAGE, bold=True)
    steps = [
        ("PDF sumber", "DOC002–DOC005"),
        ("Chunk teks", "LlamaParse"),
        ("Offset CSV", "char_start / char_end"),
        ("BuktiSumber", "kutipan + halaman + idChunk"),
        ("prov:wasDerivedFrom", "BukuDOC002 / BukuDOC005"),
    ]
    for i, (title, sub) in enumerate(steps):
        y = 2.08 + i * 0.72
        add_rect(s, 0.65, y, 5.3, 0.58, WHITE, line=LINE)
        add_rect(s, 0.65, y, 0.08, 0.58, SAGE, line=None)
        add_text(s, title, 0.85, y + 0.08, 4.9, 0.24, size=9.8, color=INK, bold=True)
        add_text(s, sub, 0.85, y + 0.3, 4.9, 0.22, size=8.4, color=MUTED)
    add_text(s, "BANK Q&A", 6.75, 1.7, 3.0, 0.3, size=9.5, color=GOLD, bold=True)
    qa = [
        ("Kenapa ontologi, bukan database?", "Reasoning definisi, bukan hanya query."),
        ("Kenapa SROIQ(D)?", "Butuh inverse, cardinality, nominal, chain."),
        ("Apakah SWRL jalan di backend?", "Belum; offline Pellet/owlready2."),
        ("Bagaimana mencegah halusinasi?", "Verbatim + offset + provenance."),
    ]
    for i, (q, a) in enumerate(qa):
        y = 2.08 + i * 0.98
        add_text(s, q, 6.75, y, 5.6, 0.28, size=10, color=INK, bold=True)
        add_text(s, a, 6.75, y + 0.28, 5.6, 0.28, size=9.2, color=MUTED)
    add_text(s, "Semua bukti disimpan sebagai node BuktiSumber; bukan ringkasan model.", 0.65, 5.9, 5.3, 0.35, size=9.0, color=MUTED)
    add_footer(s, 12)
    add_notes(s, "Backup untuk Q&A. Gunakan rantai bukti untuk menjawab pertanyaan provenance, dan bank Q&A untuk pertanyaan konsep.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(f"Wrote {OUT}")
    print(f"Slides: {len(prs.slides)}")


if __name__ == "__main__":
    build()


