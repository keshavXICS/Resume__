import os
from fastapi.responses import StreamingResponse
from bs4 import BeautifulSoup
from weasyprint import HTML
import io 
from docx import Document
import tempfile
import asyncio

def download_pdf(html_content):
    try:
        html = HTML(string=html_content)
        pdf = html.write_pdf()

        pdf_stream = io.BytesIO(pdf)    
        return StreamingResponse(pdf_stream, 
                                media_type="application/pdf",
                                headers={"Content-Disposition": 
                                        "attachment; filename=preview_page.pdf"})
    except Exception as e:
        raise f"Error while creating PDF file to download {e}"

async def download_docx(html_content):
    try:
        soup = asyncio.create_task(BeautifulSoup(html_content, "html.parser"))
        doc = asyncio.create_task(Document())
        soup = await soup
        text_content =  asyncio.create_task(soup.get_text())
        # Generate DOCX using python-docx
        text_content = await text_content
        doc = await doc
        doc.add_paragraph(text_content)
        
        # Create a temporary file to save the DOCX content
        tmp_docx = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        doc.save(tmp_docx.name)
        
        # Return the DOCX file
        with open(tmp_docx.name, "rb") as f:
            docx_data = f.read()

        os.remove(tmp_docx.name)
        
        return StreamingResponse(io.BytesIO(docx_data), media_type=
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=preview_page.docx"})
    except Exception as e:
        raise f"Error while creating Docx file to download {e}"

async def create_download_file(str: format, html_content):
    if format == "pdf":
        # Generate PDF using WeasyPrint (or any other method)
        return download_pdf(html_content)
        
    elif format == "docx":
        # Convert HTML to text using BeautifulSoup
        return download_docx(html_content)
    else:
        raise "Only support pdf and docs file"