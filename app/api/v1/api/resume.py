import os
import json
import re
import asyncio
import pdfplumber
import docx
import redis
import redis.asyncio
import google.generativeai as genai
from fastapi import HTTPException
from ..exception import CustomError
# from ....exception import CustomError
from fpdf import FPDF
from ..database.mongo_connect import collection

# Log utility function
def write_log(message: str):
    with open("log.txt", "a") as log_file:
        log_file.write(f"{message}\n")

# PDF text extraction
def extract_text_from_pdf(file_path: str) -> str:
    try:
        with pdfplumber.open(file_path) as pdf:
            return " ".join(page.extract_text() for page in pdf.pages)
    except Exception as e:
        write_log("Error extracting text from PDF")
        raise CustomError(status_code=400, detail="Failed to extract text from PDF")

# DOCX text extraction
def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        return " ".join([para.text for para in doc.paragraphs])
    except Exception as e:
        write_log(f"Error extracting text from DOCX: {e}")
        raise CustomError(status_code=400, detail="Failed to extract text from DOCX")

# Gemini AI model call
def gemini_call(text_: str, json_format: dict, model, query: str) -> dict:
    try:
        response = model.generate_content(f"resume:{text_}, json_format:{json_format} query:{query}")
        raw_text = response.candidates[0].content.parts[0].text
        match = re.search(r'```json\n(.*?)\n```', raw_text, re.DOTALL)

        if match:
            embedded_json_text = match.group(1)
            parsed_dict = json.loads(embedded_json_text)
            return parsed_dict
        else:
            return {"error": "No JSON found in response"}
    
    except Exception as e:
        write_log(f"Gemini failed: {e}")
        return {"Error": "Gemini failed"}

# Convert file to text based on file type
async def convert_into_text(file_path: str) -> str:
    try:
        if file_path.endswith(".pdf"):
            return extract_text_from_pdf(file_path)
        elif file_path.endswith(".docx"):
            return extract_text_from_docx(file_path)
        else:
            raise CustomError(status_code=400, detail="Unsupported file format")
    except Exception as e:
        write_log(f"Error converting file to text: {e}")
        raise CustomError(status_code=500, detail="File conversion failed")

# Gemini model configuration
def gemini_configure():
    try:
        my_api_key = "AIzaSyCcZr0RM0l0FTdwIHJ9SqYH_zxPW304nqM"
        genai.configure(api_key=my_api_key)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        write_log(f"Error in Gemini configuration: {e}")
        raise CustomError(status_code=500, detail="Failed to configure Gemini")

# Read files (query & JSON layout)
async def read_files() -> tuple:
    try:
        with open(f'jsonLayout.json', 'r') as blank_resume:
            json_format = json.load(blank_resume)

        with open('query.txt', 'r') as file:
            query = file.read()

        return json_format, query
    except Exception as e:
        write_log(f"Error in reading files: {e}")
        raise CustomError(status_code=500, detail="Failed to read query or JSON layout")

# Write resume to binary file
async def write_resume_binary(file) -> str:
    try:
        os.makedirs("temp", exist_ok=True)
        file_location = f"temp/{file.filename}"
        file_data = await file.read()
        with open(file_location, "wb") as f:
            f.write(file_data)
        return file_location
    except Exception as e:
        write_log(f"Error writing binary file: {e}")
        raise CustomError(status_code=500, detail="Failed to create binary file")

# Main function to fetch data
async def fetch_data(file, results):
    try:
        file_read = asyncio.create_task(read_files())
        file_location = asyncio.create_task(write_resume_binary(file))
        file_location_ = await file_location
        text = asyncio.create_task(convert_into_text(file_location_))

        model = gemini_configure()

        json_format, query = await file_read
        text_ = await text
        result = gemini_call(text_, json_format, model, query)
        
        # Extract email and phone (based on your requirements)
        email = ""
        phone = ""
        
        filter = {"$or": [{"node.resume.contactDetails.email": email}, {"node.resume.contactDetails.phone": phone}]}
        collection.replace_one(filter, result, upsert=True)
        
        results.append(result)
        os.remove(file_location_)
        return

    except HTTPException as he:
        write_log(f"HttpException: {he.detail}")
        raise he
    except Exception as e:
        write_log(f"Unexpected error: {e}")
        raise CustomError(status_code=500, detail="An unexpected error occurred")

# PDF resume generation (template example)
def generate_pdf_resume() -> str:
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
    return html_content
