"""Xuat hoa don PDF (C7)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .dao import invoice_dao, invoice_item_dao, payment_dao


class ExportError(Exception):
    pass


def _money(v: Any) -> str:
    try:
        n = float(v or 0)
    except Exception:
        n = 0.0
    return f"{int(round(n)):,}đ".replace(",", ".")


def _fmt_dt(dt: Any) -> str:
    if isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y %H:%M")
    return str(dt or "")


def _register_vietnamese_font() -> str:
    """Dang ky font co dau (Windows) neu co. Tra ve ten font de dung."""
    candidates = [
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
    ]
    for p in candidates:
        if p.exists():
            name = p.stem
            try:
                pdfmetrics.registerFont(TTFont(name, str(p)))
                return name
            except Exception:
                continue
    return "Helvetica"


def export_invoice_pdf(invoice_id: int, out_path: str | Path) -> Path:
    inv = invoice_dao.get_by_id(invoice_id)
    if inv is None:
        raise ExportError("Hóa đơn không tồn tại.")

    items = invoice_item_dao.list_by_invoice(invoice_id)
    payments = payment_dao.list_by_invoice(invoice_id)

    out = Path(out_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_vietnamese_font()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="VN", fontName=font_name, fontSize=10, leading=13))
    styles.add(ParagraphStyle(name="VN_TITLE", fontName=font_name, fontSize=16, leading=20, alignment=1))

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Hoa don {inv.get('invoice_no','')}",
    )

    story: list[Any] = []
    story.append(Paragraph("HÓA ĐƠN DỊCH VỤ CHĂM SÓC THÚ CƯNG", styles["VN_TITLE"]))
    story.append(Spacer(1, 8))

    info = [
        ["Mã hóa đơn:", str(inv.get("invoice_no", "")), "Ngày:", _fmt_dt(inv.get("issued_at"))],
        ["Trạng thái:", str(inv.get("payment_status", "")), "", ""],
    ]
    info_table = Table(info, colWidths=[25 * mm, 65 * mm, 18 * mm, 55 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 10))

    # Items table
    data = [["Thú cưng", "Dịch vụ", "SL", "Đơn giá", "Thành tiền"]]
    for it in items:
        data.append(
            [
                str(it.get("pet_name") or "—"),
                str(it.get("service_name", "")),
                str(it.get("quantity", "")),
                _money(it.get("unit_price")),
                _money(it.get("line_total")),
            ]
        )

    items_table = Table(data, colWidths=[30 * mm, 58 * mm, 12 * mm, 32 * mm, 32 * mm])
    items_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 10))

    # Totals
    totals = [
        ["Tạm tính:", _money(inv.get("subtotal_amount"))],
        ["Giảm giá:", _money(inv.get("discount_amount"))],
        ["Thuế:", _money(inv.get("tax_amount"))],
        ["Tổng cộng:", _money(inv.get("total_amount"))],
    ]
    totals_table = Table(totals, colWidths=[35 * mm, 35 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#0F172A")),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
                ("TOPPADDING", (0, -1), (-1, -1), 6),
            ]
        )
    )
    story.append(totals_table)

    # Payments list (optional)
    if payments:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Lịch sử thanh toán", styles["VN"]))
        pay_data = [["Ngày", "Phương thức", "Số tiền", "Ghi chú"]]
        for p in payments:
            pay_data.append(
                [
                    _fmt_dt(p.get("paid_at")),
                    str(p.get("method", "")),
                    _money(p.get("amount")),
                    str(p.get("note") or ""),
                ]
            )
        pay_table = Table(pay_data, colWidths=[35 * mm, 30 * mm, 30 * mm, 72 * mm])
        pay_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(pay_table)

    def _footer(canvas, _doc):  # type: ignore[no-redef]
        canvas.saveState()
        canvas.setFont(font_name, 9)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(18 * mm, 10 * mm, "Pet Care Management")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return out

