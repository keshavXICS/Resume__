import os
import re
import pdfplumber
import docx
import pandas as pd
import spacy
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from typing import List

import uvicorn
from pymongo import MongoClient
import warnings
import google.generativeai as genai
import os
import json
import asyncio


# Disable warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


# MongoDB Client Setup
client = MongoClient("mongodb://localhost:27017/")
db = client["candidate_profiles"]
collection = db["profiles"]
app = FastAPI()
lock = asyncio.Lock()
import time


        

if __name__ == '__main__':
    uvicorn.run(app, port=9000, host='0.0.0.0')

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
    
    print(f'file created at location: {file_location}')
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


@app.post("/upload/")
async def upload_resumes(files: List[UploadFile] = File(...)):
    results = []
    print('Hello')
    await fetch_data(files[0], results)
  
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
    