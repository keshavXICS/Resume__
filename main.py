from fastapi import FastAPI, Response, File, UploadFile, HTTPException
from fastapi.params import Query
from fastapi.responses import HTMLResponse, StreamingResponse
from typing import List
import os
import uvicorn
import warnings
import asyncio
import queue_utils
import fetch_resume
from fetch_resume import fetch_data
from connect_db import collection
from contextlib import asynccontextmanager
from weasyprint import HTML
import io 
from docx import Document
import pypandoc
import tempfile
from weasyprint import HTML
from bs4 import BeautifulSoup


# Disable warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('Start Up.....')
    queue_utils.delete_queue("deleting old queue")
    try:
        yield
    finally:

        print('Shutting Down.....')

app = FastAPI(lifespan=lifespan)
lock = asyncio.Lock()



if __name__ == '__main__':
    uvicorn.run(app, port=9000, host='0.0.0.0')


@app.post("/upload/")
async def upload_resumes(files: List[UploadFile] = File(...)):
    queue_utils.enqueue_message(message="User Request Added.")
    queue_utils.get_queue_length("User request inserted in queue")

    results = []
    await fetch_data(files[0], results)
    queue_utils.dequeue_message(message="User Request Completed.")
    queue_utils.get_queue_length("One User request complete")
    return results


def serialize_document(doc):
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc


@app.get("/resumes/")
async def get_resumes():
    resumes = list(collection.find())
    if not resumes:
        raise HTTPException(status_code=404, detail="No resumes found.")
    return [serialize_document(resume) for resume in resumes]




@app.get("/download-resume", response_class=HTMLResponse)
async def download_resume(format: str = Query("pdf", enum=["pdf", "docx"])):

    html_content = """
    <html>
        <head>
            <title>Preview Page</title>
        </head>
        <body>
            <h1>Your Preview Page</h1>
            <p>This is a preview of your content that will be converted to a PDF.</p>
            <ul>
                <li>Name: John Doe</li>
                <li>Email: johndoe@example.com</li>
                <li>Occupation: Software Engineer</li>
            </ul>
        </body>
    </html>
    """
    if format == "pdf":
        # Generate PDF using WeasyPrint (or any other method)
        html = HTML(string=html_content)
        pdf = html.write_pdf()

        pdf_stream = io.BytesIO(pdf)    
        return StreamingResponse(pdf_stream, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=preview_page.pdf"})

    elif format == "docx":
        # Convert HTML to text using BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text()

        # Generate DOCX using python-docx
        doc = Document()
        doc.add_paragraph(text_content)
        
        # Create a temporary file to save the DOCX content
        tmp_docx = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        doc.save(tmp_docx.name)
        
        # Return the DOCX file
        with open(tmp_docx.name, "rb") as f:
            docx_data = f.read()

        os.remove(tmp_docx.name)
        
        return StreamingResponse(io.BytesIO(docx_data), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                 headers={"Content-Disposition": "attachment; filename=preview_page.docx"})
