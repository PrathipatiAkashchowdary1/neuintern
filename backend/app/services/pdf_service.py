"""Generates real PDF files (offer letters, certificates) with reportlab.
No browser/print dependency — these bytes are the actual document.

Offer letter wording mirrors the approved docx template
(1785303083137_INTERNSHIP_OFFER_LETTER.docx) so the PDF and the original
Word letter read identically.
"""

import io
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image as RLImage,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# NeuIntern brand — solid teal (matches the logo/letterhead in the docx template)
BRAND_TEAL = colors.HexColor("#00ABBC")
INK = colors.HexColor("#150F26")
INK_MUTED = colors.HexColor("#5F5480")
CLOUD = colors.HexColor("#FAF9FE")
RULE = colors.HexColor("#E9E4F5")

PAGE_MARGIN = 22 * mm

# Real wordmark logo (backend/app/assets/logo.webp). Falls back to the plain
# "NI" square badge below if the file is missing, so this never crashes a
# fresh checkout that hasn't added a logo yet.
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
_LOGO_PATH = os.path.join(_ASSETS_DIR, "logo.webp")
_logo_reader = None
_logo_aspect = None  # height / width, used to scale proportionally
if os.path.exists(_LOGO_PATH):
    _logo_reader = ImageReader(_LOGO_PATH)
    _logo_w, _logo_h = _logo_reader.getSize()
    _logo_aspect = _logo_h / _logo_w


_MSME_PATH = os.path.join(_ASSETS_DIR, "msme_badge.webp")
_SIGNATURE_PATH = os.path.join(_ASSETS_DIR, "signature.webp")
_AICTE_PATH = os.path.join(_ASSETS_DIR, "aicte_badge.webp")


def _accreditation_badges_row():
    """MSME + AICTE badges, side by side. Returns None if either image file
    is missing, so a checkout without these assets yet doesn't crash."""
    specs = [(_MSME_PATH, 30 * mm), (_AICTE_PATH, 20 * mm)]

    cells, widths = [], []
    for path, target_width in specs:
        if not os.path.exists(path):
            return None
        reader = ImageReader(path)
        iw, ih = reader.getSize()
        height = target_width * (ih / iw)
        cells.append(RLImage(path, width=target_width, height=height))
        widths.append(target_width + 10 * mm)

    table = Table([cells], colWidths=widths)
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _signature_image(width: float = 32 * mm):
    """The signature scrawl alone, sized to sit directly above the
    "Founder" line — like a real signed letter. Returns None if the image
    file is missing.

    Note: the source PNG is a square 400x400 canvas with a lot of
    transparent padding around the actual ink strokes. The approved docx
    displayed it stretched to a wider, shorter aspect (~1.82:1) rather than
    the file's native square shape, so we match that display ratio here
    instead of reading the file's own dimensions."""
    if not os.path.exists(_SIGNATURE_PATH):
        return None
    display_aspect = 777240 / 1417320  # height/width, taken from the docx's own sizing
    height = width * display_aspect
    return RLImage(_SIGNATURE_PATH, width=width, height=height, hAlign="LEFT")


def _draw_logo(c: canvas.Canvas, x: float, y: float, width: float) -> float:
    """Draws the real logo with its bottom-left corner at (x, y), `width`
    wide with aspect ratio preserved. Returns the rendered height so callers
    can lay out whatever comes next. Falls back to the "NI" badge if no
    logo file is present."""
    if not _logo_reader:
        _logo_badge(c, x, y, size=11 * mm)
        return 11 * mm

    height = width * _logo_aspect
    c.drawImage(_logo_reader, x, y, width=width, height=height, mask="auto")
    return height


def _brand_bar(c: canvas.Canvas, x: float, y: float, width: float, height: float) -> None:
    """Solid brand-teal header bar (kept as its own helper in case the
    brand ever moves back to a two-color gradient)."""
    c.setFillColor(BRAND_TEAL)
    c.rect(x, y, width, height, stroke=0, fill=1)


def _logo_badge(c: canvas.Canvas, x: float, y: float, size: float = 11 * mm) -> None:
    c.saveState()
    c.setFillColor(BRAND_TEAL)
    c.roundRect(x, y, size, size, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", size * 0.34)
    c.drawCentredString(x + size / 2, y + size * 0.32, "NI")
    c.restoreState()


# ---------------------------------------------------------------------------
# Offer letter
# ---------------------------------------------------------------------------

def _offer_letter_header_footer(reference_id: str):
    """Returns an onPage callback that draws the brand bar, logo/wordmark,
    and a small reference-ID footer on every page of the offer letter."""

    def _draw(c: canvas.Canvas, doc):
        page_w, page_h = A4

        _brand_bar(c, 0, page_h - 6 * mm, page_w, 6 * mm)

        _draw_logo(c, PAGE_MARGIN, page_h - 24 * mm, width=34 * mm)

        c.setStrokeColor(RULE)
        c.setLineWidth(0.75)
        footer_y = 16 * mm
        c.line(PAGE_MARGIN, footer_y, page_w - PAGE_MARGIN, footer_y)

        c.setFont("Helvetica", 8)
        c.setFillColor(INK_MUTED)
        c.drawString(PAGE_MARGIN, footer_y - 6 * mm, f"Ref: {reference_id}")
        c.drawRightString(page_w - PAGE_MARGIN, footer_y - 6 * mm, "NeuIntern Programs Team")

    return _draw


def generate_offer_letter_pdf(data: dict) -> io.BytesIO:
    """data: studentName, programTitle, startDate, endDate, referenceId

    Wording matches the approved offer letter docx template exactly —
    edit the `paragraphs` list below (and keep the docx in sync) if the
    approved copy ever changes.
    """
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=42 * mm,
        bottomMargin=26 * mm,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        title=f"NeuIntern Offer Letter — {data['studentName']}",
    )

    title_style = ParagraphStyle(
        "OfferTitle", fontName="Helvetica-Bold", fontSize=18, textColor=INK, spaceAfter=4 * mm
    )
    meta_style = ParagraphStyle("Meta", fontName="Helvetica-Bold", fontSize=9, textColor=INK_MUTED)
    greeting_style = ParagraphStyle(
        "Greeting", fontName="Helvetica-Bold", fontSize=11, textColor=INK, spaceAfter=4 * mm
    )
    body_style = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=10.5,
        leading=15.5,
        textColor=INK,
        alignment=TA_JUSTIFY,
        spaceAfter=4 * mm,
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=body_style, spaceAfter=1.5 * mm, alignment=0  # left-aligned bullets read better than justified
    )
    signoff_style = ParagraphStyle("Signoff", fontName="Helvetica-Bold", fontSize=10.5, textColor=INK, spaceBefore=6 * mm)
    founder_style = ParagraphStyle("Founder", parent=signoff_style, spaceBefore=1 * mm)

    story = []
    story.append(Paragraph("INTERNSHIP OFFER LETTER", title_style))

    meta_table = Table(
        [[Paragraph(f"Date: {data['startDate']}", meta_style), Paragraph(f"ID: {data['referenceId']}", meta_style)]],
        colWidths=[doc.width / 2, doc.width / 2],
    )
    meta_table.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph(f"Dear {data['studentName']},", greeting_style))

    story.append(
        Paragraph(
            f"We are delighted to congratulate you on being selected for the "
            f"{data['programTitle']} virtual internship position with NeuIntern. "
            f"We are excited to welcome you to our team.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            f"The internship will run for 1 month, from {data['startDate']} to {data['endDate']}. "
            f"This program is designed as an educational opportunity, with the primary focus on "
            f"learning, skill development, and gaining hands-on experience. We believe you will "
            f"approach all assigned tasks and projects with dedication.",
            body_style,
        )
    )
    story.append(Paragraph("As an intern, we expect you to:", body_style))
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph("Perform all assigned tasks to the best of your ability.", bullet_style)),
                ListItem(Paragraph("Follow all lawful and reasonable instructions provided to you.", bullet_style)),
            ],
            bulletType="bullet",
            start="circle",
            leftIndent=6 * mm,
            spaceAfter=4 * mm,
        )
    )
    story.append(
        Paragraph(
            "We are confident that this internship will be a valuable experience and will "
            "contribute meaningfully to your career growth. We look forward to working with you "
            "and supporting you in achieving your professional goals.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "By accepting this offer, you commit to executing assigned tasks diligently and "
            "striving for excellence in all aspects of your work.",
            body_style,
        )
    )
    story.append(Paragraph("Best of luck, and welcome aboard!", body_style))

    story.append(Paragraph("Thank you,", signoff_style))
    story.append(Paragraph("Team NeuIntern", signoff_style))

     # 1. Append the signature first
    signature = _signature_image()
    if signature:
        story.append(Spacer(1, 8 * mm))
        story.append(signature)
    else:
        story.append(Spacer(1, 16 * mm)) # Added a bit more space if the signature is missing

    # 2. Append the Founder text directly under the signature
    story.append(Paragraph("Founder", founder_style))

    # 3. Append the MSME/AICTE badges last so they sit at the bottom
    badges = _accreditation_badges_row()
    if badges:
        story.append(Spacer(1, 12 * mm)) # Space between Founder text and badges
        story.append(badges)

    on_page = _offer_letter_header_footer(data["referenceId"])
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    buf.seek(0)
    return buf



# ---------------------------------------------------------------------------
# Certificate
# ---------------------------------------------------------------------------

def generate_certificate_pdf(data: dict) -> io.BytesIO:
    """data: studentName, programTitle, certificateId, issuedOn (display string)

    Same brand teal + logo badge + signature block as the offer letter above,
    so the two documents read as a matched pair."""
    buf = io.BytesIO()
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=landscape(A4))

    c.setFillColor(CLOUD)
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)

    border_margin = 10 * mm
    c.setStrokeColor(BRAND_TEAL)
    c.setLineWidth(2)
    c.rect(border_margin, border_margin, page_w - 2 * border_margin, page_h - 2 * border_margin, stroke=1, fill=0)

    _brand_bar(c, border_margin, page_h - border_margin - 4 * mm, page_w - 2 * border_margin, 4 * mm)

    center_x = page_w / 2

    logo_width = 46 * mm
    _draw_logo(c, center_x - logo_width / 2, page_h - 46 * mm, width=logo_width)

    c.setFillColor(BRAND_TEAL)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(center_x, page_h - 56 * mm, "CERTIFICATE OF COMPLETION")

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(center_x, page_h - 74 * mm, data["studentName"])

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica", 12)
    c.drawCentredString(center_x, page_h - 88 * mm, "has successfully completed the 1-month")

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(center_x, page_h - 96 * mm, f"{data['programTitle']} internship program")

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica", 12)
    c.drawCentredString(center_x, page_h - 104 * mm, "at NeuIntern")

    # Signature block, mirroring the offer letter's sign-off
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(center_x, 30 * mm, "Founder, NeuIntern")

    c.setFont("Helvetica", 9)
    footer_y = border_margin + 12 * mm
    c.setFillColor(INK_MUTED)
    c.drawString(border_margin + 14 * mm, footer_y, f"VERIFIED ID: {data['certificateId']}")
    if data.get("issuedOn"):
        c.drawRightString(page_w - border_margin - 14 * mm, footer_y, f"ISSUED: {data['issuedOn']}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Payment invoice / receipt
# ---------------------------------------------------------------------------

def generate_invoice_pdf(data: dict) -> io.BytesIO:
    """data: invoiceNumber, invoiceDate (display string), studentName, email,
    phone, programTitle, amount, currency, paymentId, orderId"""

    buf = io.BytesIO()
    page_w, page_h = A4
    c = canvas.Canvas(buf, pagesize=A4)

    # GST Calculation (18% Inclusive)
    total_amount = float(data["amount"])
    taxable_amount = round(total_amount / 1.18, 2)
    gst_amount = round(total_amount - taxable_amount, 2)
    cgst = round(gst_amount / 2, 2)
    sgst = round(gst_amount / 2, 2)

    # ------------------------------------------------
    # Header
    # ------------------------------------------------
    _brand_bar(c, 0, page_h - 6 * mm, page_w, 6 * mm)
    _draw_logo(c, PAGE_MARGIN, page_h - 24 * mm, width=34 * mm)

    c.setFillColor(BRAND_TEAL)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(page_w - PAGE_MARGIN, page_h - 16 * mm, "PAID")

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(PAGE_MARGIN, page_h - 44 * mm, "Payment Receipt")

    c.setFont("Helvetica", 9)
    c.setFillColor(INK_MUTED)
    c.drawString(
        PAGE_MARGIN,
        page_h - 52 * mm,
        f"Invoice: {data['invoiceNumber']}"
    )

    c.drawRightString(
        page_w - PAGE_MARGIN,
        page_h - 52 * mm,
        f"Date: {data['invoiceDate']}"
    )

    # ------------------------------------------------
    # Company Details
    # ------------------------------------------------
    company_y = page_h - 62 * mm

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(PAGE_MARGIN, company_y, "ISSUED BY")

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(PAGE_MARGIN, company_y - 6 * mm, "VividOne Pvt. Ltd.")

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica", 9)

    text = c.beginText(PAGE_MARGIN, company_y - 12 * mm)
    text.textLine("#Flat no 401, Vasista Enclave, A.S.Raju Nagar, KPHB,")
    text.textLine("Hyderabad, Telangana 500072, India")
    text.textLine("GSTIN: 36AAHCV0625N1Z1")
    text.textLine("Email: contact@neuintern.com")
    text.textLine("Phone: +91 9652522929")
    c.drawText(text)

    # ------------------------------------------------
    # Billed To
    # ------------------------------------------------
    y = page_h - 102 * mm

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(PAGE_MARGIN, y, "BILLED TO")

    c.setFont("Helvetica", 10)
    c.setFillColor(INK)
    c.drawString(PAGE_MARGIN, y - 6 * mm, data["studentName"])

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(PAGE_MARGIN, y - 12 * mm, data["email"])
    c.drawString(PAGE_MARGIN, y - 18 * mm, data["phone"])

    # ------------------------------------------------
    # Table
    # ------------------------------------------------
    table_y = y - 34 * mm
    row_h = 9 * mm

    c.setStrokeColor(RULE)
    c.setLineWidth(0.75)

    c.setFillColor(INK_MUTED)
    c.setFont("Helvetica-Bold", 8)

    c.drawString(PAGE_MARGIN, table_y, "DESCRIPTION")
    c.drawRightString(page_w - PAGE_MARGIN, table_y, "AMOUNT")

    c.line(
        PAGE_MARGIN,
        table_y - 3 * mm,
        page_w - PAGE_MARGIN,
        table_y - 3 * mm
    )

    c.setFont("Helvetica", 10)
    c.setFillColor(INK)

    item_y = table_y - 3 * mm - row_h

    c.drawString(
        PAGE_MARGIN,
        item_y,
        f"Certificate processing fee — {data['programTitle']} internship"
    )

    c.drawRightString(
        page_w - PAGE_MARGIN,
        item_y,
        f"{data['currency']} {taxable_amount:.2f}"
    )

    item_y -= row_h

    c.drawString(PAGE_MARGIN, item_y, "CGST @ 9%")
    c.drawRightString(
        page_w - PAGE_MARGIN,
        item_y,
        f"{data['currency']} {cgst:.2f}"
    )

    item_y -= row_h

    c.drawString(PAGE_MARGIN, item_y, "SGST @ 9%")
    c.drawRightString(
        page_w - PAGE_MARGIN,
        item_y,
        f"{data['currency']} {sgst:.2f}"
    )

    total_y = item_y - row_h

    c.line(
        PAGE_MARGIN,
        total_y + 4 * mm,
        page_w - PAGE_MARGIN,
        total_y + 4 * mm
    )

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(INK)

    c.drawString(PAGE_MARGIN, total_y, "Total Paid")
    c.drawRightString(
        page_w - PAGE_MARGIN,
        total_y,
        f"{data['currency']} {total_amount:.2f}"
    )

    # ------------------------------------------------
    # Payment Details
    # ------------------------------------------------
    meta_y = total_y - 16 * mm

    c.setFont("Helvetica", 8)
    c.setFillColor(INK_MUTED)

    c.drawString(
        PAGE_MARGIN,
        meta_y,
        f"Payment ID: {data['paymentId']}"
    )

    c.drawString(
        PAGE_MARGIN,
        meta_y - 5 * mm,
        f"Order ID: {data['orderId']}"
    )

    c.drawString(
        PAGE_MARGIN,
        meta_y - 10 * mm,
        "Payment Method: Razorpay"
    )

    # ------------------------------------------------
    # Footer
    # ------------------------------------------------
    footer_y = 16 * mm

    c.setStrokeColor(RULE)
    c.line(PAGE_MARGIN, footer_y, page_w - PAGE_MARGIN, footer_y)

    c.setFont("Helvetica", 8)
    c.setFillColor(INK_MUTED)

    c.drawString(
        PAGE_MARGIN,
        footer_y - 6 * mm,
        "NeuIntern Programs Team"
    )

    c.drawString(
        PAGE_MARGIN,
        footer_y - 10 * mm,
        "A Product of VividOne Pvt. Ltd."
    )

    c.drawRightString(
        page_w - PAGE_MARGIN,
        footer_y - 6 * mm,
        "This is a system-generated receipt."
    )

    c.showPage()
    c.save()

    buf.seek(0)
    return buf