from fastapi import FastAPI, Response, Depends, Request, File, UploadFile, HTTPException
from fastapi.params import Query
from fastapi.responses import HTMLResponse, StreamingResponse
from typing import List
import os
import uvicorn
import warnings
import asyncio
import queue_utils
from api.v1.api.remume import fetch_data
from api.v1.database.mongo_connect import collection
from contextlib import asynccontextmanager

import mysql.connector
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
from fastapi.responses import RedirectResponse
from google.oauth2 import id_token
from fastapi.security import OAuth2PasswordBearer

from api.v1.auth.googleAuth import google_auth
from api.v1.auth.googleAuth import google_user_data     
from api.v1.api.auth import registerUser, loginUser, verify_token
from api.v1.api.download import create_download_file

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

pwd_context =  CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI(lifespan=lifespan)
lock = asyncio.Lock()

mysql_host = os.getenv("MYSQL_HOST", "mysql")
mysql_user = os.getenv("MYSQL_USER", "root")
mysql_password = os.getenv("MYSQL_PASSWORD", "rootpassword")
mysql_db = os.getenv("MYSQL_DB", "fastapidb")

if __name__ == '__main__':
    uvicorn.run(app, port=9000, host='0.0.0.0')


class UserSignup(BaseModel):
    # id: int
    username: str
    email: str
    phone: Optional[str] = None
    password: str
    
    # class Config:
    #     orm_mode = True

class UserIn(BaseModel):
    email: str
    password: str

def hash_password(password: str)->str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str )-> bool:
    return pwd_context.verify(plain_password, hashed_password)



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

# Download output PDF and docs
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
    return create_download_file(format, html_content)
# signup user
@app.post("/signUp")
async def read_root(user: UserSignup):
    try:
        create_user = asyncio.create_task(registerUser(user))
        return await create_user
        
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Query failed: {err}")



# google auth

@app.get("/auth/google")
def google_login():
    try:
        return RedirectResponse(google_auth())
    except:
        return {"message": "Google Authentication Fail"}

# google auth successfull

@app.get('/auth/done')
async def get_data(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Authentication code not provided"}
    data = await google_user_data(code)
    return data
    


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# jwt validation
@app.post("/login")
async def login(user:UserIn):
    result = loginUser(user)
    return result

# jwt exist
@app.get("/protected")
def protected_route(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"message": f"Welcome, {payload}"}


