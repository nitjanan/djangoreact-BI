"""สร้างไฟล์ PDF ของรายงาน (fpdf2 + HarfBuzz เพื่อวางสระ/วรรณยุกต์ไทยให้ถูกตำแหน่ง)

ฟอนต์ IBM Plex Sans Thai (OFL) ตัวเดียวกับหน้าเว็บ แปลงจาก @fontsource (thai + latin)
"""

from pathlib import Path

from fpdf import FPDF, FontFace
from fpdf.enums import TableBordersLayout

from .period import thai_date, thai_month

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT = "Plex"

INK = (18, 48, 58)
MUTED = (96, 116, 122)
LINE = (211, 226, 228)
SOFT = (240, 246, 247)
ACCENT = (13, 110, 120)
BAD = (184, 50, 38)
GOOD = (30, 122, 72)

DASH = "–"


def fmt(value, digits=0):
    if value is None:
        return DASH
    return f"{value:,.{digits}f}"


def change(value, base):
    """% เปลี่ยนแปลงจาก base (None = เทียบไม่ได้)"""
    if value is None or not base:
        return None
    return (value - base) / base * 100


def car_name(code, name):
    return f"{code} {name}".strip() or DASH


def thai_datetime(dt):
    return f"{thai_date(dt)} {dt:%H:%M} น." if dt else DASH


class ReportPDF(FPDF):
    def __init__(self, report):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report = report
        self.period = report["period"]
        self.set_margins(14, 16, 14)
        self.set_auto_page_break(True, margin=16)
        self.add_font(FONT, "", FONT_DIR / "IBMPlexSansThai-Regular.ttf")
        self.add_font(FONT, "B", FONT_DIR / "IBMPlexSansThai-SemiBold.ttf")
        self.set_text_shaping(True)
        self.set_title(f"{self.period.title} {self.period.label}")
        self.set_creator("STG Dashboard")
        self.alias_nb_pages()

    # ---------------------------------------------------------- page chrome

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font(FONT, "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, f"{self.period.title} · {self.period.label}", align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font(FONT, "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, f"หน้า {self.page_no()}/{{nb}}", align="R")

    # -------------------------------------------------------------- helpers

    def text_line(self, text, size=10, style="", color=INK, h=None, align="L"):
        self.set_font(FONT, style, size)
        self.set_text_color(*color)
        self.multi_cell(0, h or size * 0.5, text, align=align, new_x="LMARGIN", new_y="NEXT")

    def heading(self, text, note=None):
        # หัวข้อต้องมีเนื้อหาตามอย่างน้อยหนึ่งช่วง ไม่ค้างอยู่ท้ายหน้า
        if self.will_page_break(45):
            self.add_page()
        self.ln(4)
        self.text_line(text, 12, "B", h=7)
        if note:
            self.text_line(note, 8, color=MUTED, h=4.5)
        self.ln(1.5)

    def empty(self, text):
        self.text_line(text, 9, color=MUTED, h=6)

    def link_line(self, text, url, size=9):
        """ข้อความลิงก์ (กดใน PDF เปิด dashboard)"""
        self.set_font(FONT, "BU", size)
        self.set_text_color(*ACCENT)
        self.cell(self.get_string_width(text) + 1, size * 0.55, text, link=url)
        self.ln(size * 0.55)

    def table(self, headings, rows, widths, align, bold_last=False, links=None):
        self.set_font(FONT, "", 8.5)
        self.set_text_color(*INK)
        self.set_draw_color(*LINE)
        self.set_fill_color(255, 255, 255)
        with super().table(
            col_widths=widths,
            text_align=align,
            headings_style=FontFace(emphasis="BOLD", color=MUTED, fill_color=SOFT),
            borders_layout=TableBordersLayout.HORIZONTAL_LINES,
            line_height=5,
            padding=(1.2, 1.5),
            v_align="M",
        ) as t:
            t.row(headings)
            for i, r in enumerate(rows):
                last = bold_last and i == len(rows) - 1
                row = t.row(style=FontFace(emphasis="BOLD") if last else None)
                link = links[i] if links and i < len(links) else None
                for j, c in enumerate(r):
                    # คอลัมน์แรกเป็นลิงก์ (ถ้ามี) สีเดียวกับลิงก์อื่น
                    style = FontFace(color=ACCENT) if link and j == 0 else None
                    row.cell(str(c), link=link if j == 0 else None, style=style)
        self.ln(2)

    def kpi_tiles(self, kpis, per_row=4):
        gap = 3
        width = (self.epw - gap * (per_row - 1)) / per_row
        for i in range(0, len(kpis), per_row):
            row = kpis[i : i + per_row]
            compared = any(k["prev"] is not None or k["last_year"] is not None for k in row)
            height = 25 if compared else 16
            if self.will_page_break(height + 2):
                self.add_page()
            y = self.get_y()
            for j, kpi in enumerate(row):
                self._kpi_tile(kpi, self.l_margin + j * (width + gap), y, width, height)
            self.set_xy(self.l_margin, y + height + gap)

    def _kpi_tile(self, kpi, x, y, w, h):
        self.set_draw_color(*LINE)
        self.set_fill_color(255, 255, 255)
        self.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=1.5)
        pad = 3
        self.set_xy(x + pad, y + 2)
        self.set_font(FONT, "", 8)
        self.set_text_color(*MUTED)
        self.cell(w - 2 * pad, 4.5, kpi["label"])
        self.set_xy(x + pad, y + 7)
        self.set_font(FONT, "B", 13)
        self.set_text_color(*INK)
        value = fmt(kpi["value"], kpi["digits"])
        self.cell(self.get_string_width(value) + 1, 7, value)
        if kpi["value"] is not None:
            self.set_font(FONT, "", 8)
            self.set_text_color(*MUTED)
            self.cell(w, 7.4, kpi["unit"])
        lines = [
            (self.period.prev_name, kpi["prev"]),
            ("ปีก่อน", kpi["last_year"]),
        ]
        if kpi["prev"] is None and kpi["last_year"] is None:
            return
        for k, (name, base) in enumerate(lines):
            self.set_xy(x + pad, y + 15 + k * 4.3)
            self._delta(name, kpi, base, w - 2 * pad)

    def _delta(self, name, kpi, base, w):
        pct = change(kpi["value"], base)
        self.set_font(FONT, "", 7.5)
        self.set_text_color(*MUTED)
        label = f"{name} {fmt(base, kpi['digits'])} "
        self.cell(self.get_string_width(label), 4, label)
        if pct is None:
            return
        if abs(pct) < 0.5:
            self.cell(w, 4, "เท่าเดิม")
            return
        worse = (pct > 0) == kpi["lower_is_better"]
        self.set_text_color(*(BAD if worse else GOOD))
        self.set_font(FONT, "B", 7.5)
        self.cell(w, 4, f"{'↑' if pct > 0 else '↓'} {abs(pct):,.0f}%")

    # ------------------------------------------------------------- sections

    def cover(self):
        r = self.report
        p = self.period
        self.add_page()
        self.set_fill_color(*ACCENT)
        self.rect(0, 0, self.w, 3, style="F")
        self.ln(2)
        self.text_line("STG Dashboard", 9, "B", color=ACCENT, h=5)
        self.text_line(p.title, 20, "B", h=10)
        self.text_line(p.label, 13, h=7)
        self.ln(2)
        companies = (
            f"ทุกบริษัท ({len(r['companies'])} บริษัท)"
            if r["all_companies"]
            else ", ".join(r["companies"]) or DASH
        )
        self.text_line(f"บริษัท: {companies}", 9, color=MUTED, h=5)
        self.text_line(
            f"ข้อมูลจาก webstock ล่าสุด: {thai_datetime(r['last_synced_at'])}"
            f"   ·   สร้างรายงาน: {thai_datetime(r['generated_at'])}",
            9,
            color=MUTED,
            h=5,
        )
        self.ln(1)
        self.link_line("เปิด dashboard แบบเต็ม", r["url"])
        self.link_line(f"ดู{r['year_label']}", r["year_url"])

        self.heading(
            "ภาพรวมทุกแผนก",
            f"ค่าซ่อม น้ำมัน ชั่วโมงทำงาน = {p.monthly_label} · "
            f"แจ้งซ่อม = {p.label} · ใบค้างและรถที่ต้องจับตา = สถานะ ณ วันที่สร้างรายงาน",
        )
        deps = r["departments"]
        if not deps:
            self.empty("ไม่มีข้อมูลในช่วงนี้")
            return

        def kpi(dep, key):
            return next(k["value"] for k in dep["monthly_kpis"] if k["key"] == key)

        rows = [
            [
                d["name"],
                fmt(kpi(d, "repair")),
                fmt(kpi(d, "oil")),
                fmt(kpi(d, "work")),
                fmt(d["breakdown_count"]),
                fmt(d["open_jobs"]["total"]),
                fmt(d["watchlist"]["count"]),
            ]
            for d in deps
        ]
        rows.append(
            [
                "รวม",
                fmt(sum(kpi(d, "repair") or 0 for d in deps)),
                fmt(sum(kpi(d, "oil") or 0 for d in deps)),
                fmt(sum(kpi(d, "work") or 0 for d in deps)),
                fmt(sum(d["breakdown_count"] for d in deps)),
                fmt(sum(d["open_jobs"]["total"] for d in deps)),
                fmt(sum(d["watchlist"]["count"] for d in deps)),
            ]
        )
        self.table(
            ["แผนก", "ค่าซ่อม (บาท)", "น้ำมัน (ลิตร)", "ชม.ทำงาน", "แจ้งซ่อม", "ใบค้าง", "ต้องจับตา"],
            rows,
            (34, 22, 18, 15, 12, 12, 13),
            ("LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"),
            bold_last=True,
            links=[d["url"] for d in deps],
        )
        if p.is_weekly:
            self.text_line(
                "หมายเหตุ: ค่าซ่อม น้ำมัน และชั่วโมงทำงานบันทึกเป็นรายเดือน รายงานรายสัปดาห์จึงแสดง"
                "เป็นยอดสะสมของเดือน (ยังไม่เทียบกับช่วงก่อน เพราะยังไม่ครบเดือน)",
                8,
                color=MUTED,
                h=4.5,
            )

    def department(self, d):
        p = self.period
        self.add_page()
        self.text_line(d["name"], 16, "B", h=8)
        self.text_line(f"{d['noun']} {fmt(d['car_count'])} คัน (ที่มีข้อมูลตั้งแต่ต้นปี)", 9, color=MUTED, h=5)
        self.link_line(f"ดู{d['name']}แบบเต็มใน dashboard", d["url"], size=8.5)

        self.heading("ตัวเลขหลัก", p.monthly_label)
        self.kpi_tiles(d["monthly_kpis"])
        self.heading("การเสียและการซ่อม", f'ใบแจ้งซ่อมประเภท "ซ่อม" · {p.label}')
        self.kpi_tiles(d["breakdown_kpis"], per_row=4)

        self.heading(f"แจ้งซ่อมใน{('สัปดาห์' if p.is_weekly else 'เดือน')}นี้")
        if d["breakdowns"]:
            more = d["breakdown_count"] - len(d["breakdowns"])
            self.table(
                ["วันที่แจ้ง", d["noun"], "บริษัท", "อาการ", "สถานะ"],
                [
                    [
                        thai_date(b["reported_at"]),
                        car_name(b["code"], b["name"]),
                        b["company"] or DASH,
                        b["broke_reason"] or DASH,
                        "ซ่อมเสร็จ" if b["closed"] else "ยังไม่ปิด",
                    ]
                    for b in d["breakdowns"]
                ],
                (20, 34, 32, 64, 18),
                ("LEFT", "LEFT", "LEFT", "LEFT", "LEFT"),
            )
            if more > 0:
                self.empty(f"และอีก {more} ใบ ดูทั้งหมดในหน้า dashboard")
        else:
            self.empty("ไม่มีการแจ้งซ่อม")

        oj = d["open_jobs"]
        self.heading(
            "ใบแจ้งซ่อมที่ยังไม่ปิดงาน",
            f"ทั้งหมด {fmt(oj['total'])} ใบ ({fmt(oj['car_count'])} คัน) · "
            f"ค้างเกิน {oj['stale_days']} วัน {fmt(oj['stale_count'])} ใบ · "
            f"เคลื่อนย้ายไม่ได้ {fmt(oj['immobile_car_count'])} คัน · แสดง 10 ใบที่ค้างนานสุด",
        )
        if oj["jobs"]:
            self.table(
                ["เลขที่", d["noun"], "อาการ", "ค้าง (วัน)", "ขั้นตอน"],
                [
                    [
                        j["ref_no"] or DASH,
                        car_name(j["code"], j["name"] or "")
                        + (" (เคลื่อนย้ายไม่ได้)" if j["immobile"] else ""),
                        j["broke_reason"] or DASH,
                        fmt(j["days"]),
                        j["stage_label"],
                    ]
                    for j in oj["jobs"]
                ],
                (26, 40, 52, 16, 34),
                ("LEFT", "LEFT", "LEFT", "RIGHT", "LEFT"),
            )
        else:
            self.empty("ไม่มีใบค้าง")

        wl = d["watchlist"]
        self.heading(
            f"{d['noun']}ที่ต้องจับตา",
            f"{fmt(wl['count'])} คัน · เทียบกับ{d['noun']}ส่วนใหญ่ ตั้งแต่ต้นปี · แสดง 10 คันแรก",
        )
        if wl["cars"]:
            self.table(
                [d["noun"], "บริษัท", "เรื่องที่ต้องดู"],
                [
                    [
                        car_name(c["code"], c["name"] or ""),
                        c["branch_company_name"] or DASH,
                        "\n".join(f"{r['label']}: {r['detail']}" for r in c["reasons"]),
                    ]
                    for c in wl["cars"]
                ],
                (38, 32, 98),
                ("LEFT", "LEFT", "LEFT"),
            )
        else:
            self.empty("ไม่มีคันที่ติดเกณฑ์")

        self.heading(
            "ต้นทุนซ่อมต่อชั่วโมงทำงานสูงสุด 10 อันดับ",
            f"ตั้งแต่ต้นปีถึงเดือน{thai_month(p.year, p.month)}",
        )
        if d["top_cost"]:
            self.table(
                ["#", d["noun"], "บริษัท", "ชม.ทำงาน", "ค่าซ่อม (บาท)", "บาท/ชม."],
                [
                    [
                        i,
                        car_name(c["code"], c["name"]),
                        c["company"] or DASH,
                        fmt(c["work_total"]),
                        fmt(c["repair_total"]),
                        fmt(c["repair_cost_per_hr"]),
                    ]
                    for i, c in enumerate(d["top_cost"], 1)
                ],
                (7, 42, 40, 22, 30, 25),
                ("RIGHT", "LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT"),
            )
        else:
            self.empty("ยังไม่มีชั่วโมงทำงานให้คำนวณ")


def render_pdf(report):
    pdf = ReportPDF(report)
    pdf.cover()
    for d in report["departments"]:
        pdf.department(d)
    return bytes(pdf.output())


def report_filename(period):
    return f"fleet-report-{period.frequency}-{period.start:%Y-%m-%d}.pdf"
