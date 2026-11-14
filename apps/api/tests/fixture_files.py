"""Generated, non-personal fixtures; never copy user documents into tests."""

import io


def image_fixture(extension: str = ".png") -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1500, 420), "white")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
    ImageDraw.Draw(image).multiline_text(
        (50, 60),
        "DỮ LIỆU KIỂM THỬ\nPhường mẫu có mã SEN-XANH-482.\nGiờ tiếp nhận: 08:00 đến 11:00.",
        font=font,
        fill="black",
        spacing=24,
    )
    output = io.BytesIO()
    image.save(output, format="JPEG" if extension == ".jpg" else "PNG")
    return output.getvalue()


def file_fixture(extension: str) -> bytes:
    output = io.BytesIO()
    if extension in {".png", ".jpg"}:
        return image_fixture(extension)
    if extension in {".pdf", ".scan.pdf"}:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas

        document = canvas.Canvas(output)
        if extension == ".scan.pdf":
            document.drawImage(ImageReader(io.BytesIO(image_fixture())), 25, 400, width=550, height=154)
        else:
            document.drawString(40, 750, "FIXTURE ONLY. Page one: SEN-XANH-482.")
            document.showPage()
            document.drawString(40, 750, "Page two contains the separate code MAI-VANG-739.")
        document.save()
    elif extension == ".docx":
        from docx import Document

        document = Document()
        document.sections[0].header.paragraphs[0].text = "ĐƠN VỊ KIỂM THỬ"
        document.add_heading("Thủ tục minh họa", level=1)
        document.add_paragraph("DỮ LIỆU GIẢ. Mã SEN-XANH-482.")
        table = document.add_table(rows=2, cols=2)
        for row, values in zip(table.rows, [("Tên", "Mã"), ("Mai vàng", "MAI-739")], strict=True):
            for cell, value in zip(row.cells, values, strict=True):
                cell.text = value
        document.save(output)
    elif extension == ".xlsx":
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Công khai"
        sheet.append(["Thủ tục", "Phí", "Tổng"])
        sheet.append(["Sen xanh SEN-XANH-482", 12000, "=B2*2"])
        sheet.merge_cells("A3:B3")
        sheet["A3"] = "Ô gộp minh họa"
        hidden = workbook.create_sheet("Nội bộ")
        hidden.append(["HIDDEN-SECRET-915"])
        hidden.sheet_state = "hidden"
        workbook.save(output)
    elif extension == ".pptx":
        from pptx import Presentation

        document = Presentation()
        for title in ["SEN-XANH-482", "MAI-VANG-739"]:
            slide = document.slides.add_slide(document.slide_layouts[1])
            slide.shapes.title.text = title
        document.save(output)
    else:
        return {
            ".txt": "DỮ LIỆU GIẢ. Sen xanh có mã SEN-XANH-482.",
            ".md": "# Sen xanh\nMã SEN-XANH-482.\n\n# Mai vàng\nMã MAI-VANG-739.",
            ".csv": "Thủ tục;Mã\nSen xanh;SEN-XANH-482\nMai vàng;MAI-VANG-739",
            ".html": "<html><script>STEAL_SECRET()</script><nav>MENU</nav><main><h1>Sen xanh</h1><p>SEN-XANH-482</p><img src='http://forbidden.invalid/tracker'></main></html>",
        }[extension].encode()
    return output.getvalue()
