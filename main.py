from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List

import uvicorn
import warnings
import asyncio
import queue_utils
from fetch_resume import fetch_data
from connect_db import collection
from contextlib import asynccontextmanager

# Disable warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('Start Up.....')
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
    