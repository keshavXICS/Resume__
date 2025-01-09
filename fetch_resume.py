import asyncio
import pdfminer, pdfplumber
import docx
import re
import queue_utils
import redis, redis.asyncio

import google.generativeai as genai
import os
import json
from connect_db import collection


def write_log(message: str):
    with open("log.txt", "a") as log_file:
        log_file.write(f"{message}\n")

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            return " ".join(page.extract_text() for page in pdf.pages)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

# Function to extract text from DOCX
def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return " ".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""

def gemini_call(text_, json_format, model, query):
    try:
        print('Gemini model call')
        response = model.generate_content(f"resume:{text_}, json_format:{json_format} query:{query}")
        print('raw data parsing')
        raw_text = response.candidates[0].content.parts[0].text
        match = re.search(r'```json\n(.*?)\n```', raw_text, re.DOTALL)

        if match:
            print('load json file')
            embedded_json_text = match.group(1)
            parsed_dict = json.loads(embedded_json_text)
            return parsed_dict
        else:
            return {"error": "No JSON found in response"}
    
    except Exception as e:
        print(f"Error Gemini: {e}")
        return {"Error": "Gemini failed"}
    
async def convert_into_text(file_path):
    try:
        print("Convert file data into binary text")
        if file_path.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif file_path.endswith(".docx"):
            text = extract_text_from_docx(file_path)
        else:
            return {"Error": "Unsupported file format"}
        return text

    except Exception as e:
        print(f"Error parsing resume: {e}")
        return {"Error": "Parsing failed"}

def gemini_configure():
    my_api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=my_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    return model

async def read_files():
    print('Query and JSON file reading')
 
    with open(f'jsonLayout.json', 'r') as blank_resume:
        json_format = json.load(blank_resume)

    with open('query.txt', 'r') as file:
        query = file.read()

    return json_format, query

async def write_resume_binary(file):
    file_location = f"temp/{file.filename}"
    file_data = await file.read()
    print("Building sample file")
    with open(file_location, "wb") as f:
        f.write(file_data)
    return file_location


async def fetch_data(file, results):
    file_read = asyncio.create_task(read_files())
    
    file_location = asyncio.create_task(write_resume_binary(file))
    
    # print(f'file created at location: {file_location}')
    file_location_ = await file_location
    text = asyncio.create_task(convert_into_text(file_location_))

    print('Gemini configuration')
    model = gemini_configure()

    json_format, query = await file_read
    text_ = await text
    print('Calling Gemini')
    result = gemini_call(text_, json_format, model, query)
    
    print('Insert data in DB')
    collection.insert_one(result)
    result['_id'] = str(result['_id'])
    results.append(result)        
    os.remove(file_location_)
    return
