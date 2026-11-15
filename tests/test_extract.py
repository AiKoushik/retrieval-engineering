from email.message import EmailMessage

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from rx.extract import extract, extract_email, extract_pdf


def test_pdf_keeps_running_headers(tmp_path):
    path = tmp_path / "two_pages.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for page in (1, 2):
        pdf.drawString(50, 800, "ACME controlled document")
        pdf.drawString(50, 700, f"Body of page {page}")
        pdf.showPage()
    pdf.save()
    text = extract_pdf(path)
    assert text.count("ACME controlled document") == 2
    assert "Body of page 2" in text


def test_email_gives_headers_body_and_attachment_names(tmp_path):
    msg = EmailMessage()
    msg["From"], msg["To"] = "a@x.example", "b@y.example"
    msg["Subject"] = "Lot H-1 report"
    msg.set_content("Report attached.")
    msg.add_attachment(b"%PDF secret table", maintype="application",
                       subtype="pdf", filename="TR-1.pdf")
    path = tmp_path / "m.eml"
    path.write_bytes(msg.as_bytes())
    text = extract_email(path)
    assert "Subject: Lot H-1 report" in text
    assert "Report attached." in text
    assert "Attachments: TR-1.pdf" in text
    assert "secret table" not in text      # naive: names only


def test_plain_text_and_nul_bytes(tmp_path):
    path = tmp_path / "fax.txt"
    path.write_bytes(b"H-O4l8\x00 tensile 298 MPa")
    assert extract(path) == "H-O4l8 tensile 298 MPa"
