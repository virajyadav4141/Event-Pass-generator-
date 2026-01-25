import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from io import BytesIO

def generate_pass_pdf(event_name, event_date, sponsors, passes,
                      qr_width=150, qr_height=150, qr_margin=10,
                      output_file="generated_pdfs/passes.pdf"):
    """
    Generate PDF in memory (BytesIO) or file path
    """
    is_buffer = isinstance(output_file, BytesIO)
    if not is_buffer:
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

    c = canvas.Canvas(output_file, pagesize=A4)
    page_width, page_height = A4

    cols = 2
    rows = 5
    x_spacing = (page_width - cols * qr_width) / (cols + 1)
    y_spacing = (page_height - rows * qr_height) / (rows + 1)

    count = 0
    for p in passes:
        col = count % cols
        row = (count // cols) % rows
        x = x_spacing + col * (qr_width + x_spacing)
        y = page_height - ((row + 1) * (qr_height + y_spacing))

        # QR code
        qr_img = qrcode.make(p['code'])
        qr_img = qr_img.resize((qr_width, qr_height))
        img_reader = ImageReader(qr_img)
        c.drawImage(img_reader, x, y, width=qr_width, height=qr_height)

        # Font sizes
        event_font_size = 10
        pass_id_font_size = 8
        other_font_size = 9

        text_y = y + qr_height + 5

        # Event name
        c.setFont("Helvetica-Bold", event_font_size)
        c.drawString(x, text_y, f"Event: {event_name}")

        # Pass ID above date
        c.setFont("Helvetica-Bold", pass_id_font_size)
        c.drawString(x, text_y + 12, f"Pass ID: {p['code']}")

        # Date below pass ID
        c.setFont("Helvetica", other_font_size)
        c.drawString(x, text_y + 24, f"Date: {event_date}")

        # Sponsors below date
        if sponsors:
            c.drawString(x, text_y + 36, f"Sponsors: {sponsors}")

        count += 1
        if count % (cols * rows) == 0:
            c.showPage()

    c.save()
