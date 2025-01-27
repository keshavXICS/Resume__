import os
from fastapi.responses import StreamingResponse
from bs4 import BeautifulSoup
from weasyprint import HTML
import io
from docx import Document
import tempfile
from ..exception import CustomError

async def generate_pdf(html_content: str) -> StreamingResponse:
    try:
        # Generate PDF using WeasyPrint
        html = HTML(string=html_content)
        pdf = html.write_pdf()

        pdf_stream = io.BytesIO(pdf)
        return StreamingResponse(pdf_stream, 
                                 media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=preview_page.pdf"})
    except Exception as e:
        raise CustomError(status_code=500, detail=f"Error while creating PDF file: {e}")

async def generate_docx(html_content: str) -> StreamingResponse:
    try:
        # Parse HTML content with BeautifulSoup and generate DOCX
        soup = BeautifulSoup(html_content, "html.parser")
        doc = Document()
        text_content = soup.get_text()

        doc.add_paragraph(text_content)
        
        # Save the DOCX to a temporary file
        tmp_docx = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        doc.save(tmp_docx.name)

        # Return the DOCX file
        with open(tmp_docx.name, "rb") as f:
            docx_data = f.read()

        os.remove(tmp_docx.name)

        return StreamingResponse(io.BytesIO(docx_data), 
                                 media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                 headers={"Content-Disposition": "attachment; filename=preview_page.docx"})
    except Exception as e:
        raise CustomError(status_code=500, detail=f"Error while creating Docx file: {e}")

async def create_download_file(format: str, html_content: str) -> StreamingResponse:
    if format == "pdf":
        return await generate_pdf(html_content)
    elif format == "docx":
        return await generate_docx(html_content)
    else:
        raise CustomError(status_code=400, detail="Only PDF and DOCX formats are supported")
