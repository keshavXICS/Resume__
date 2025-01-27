from fastapi import FastAPI, Response, Depends, Request, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.params import Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn
import asyncio
import warnings
import mysql.connector
from contextlib import asynccontextmanager
from passlib.context import CryptContext
from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import queue_utils
from api.v1.api.resume import fetch_data
from api.v1.database.mongo_connect import collection
from api.v1.api.auth import register_user, login_user, verify_token
from api.v1.api.download import create_download_file
from api.v1.auth.googleAuth import google_auth, google_user_data

# Disable warnings
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

# Async lifespan for app
@asynccontextmanager
async def lifespan(app: FastAPI):
    print('Start Up.....')
    queue_utils.delete_queue("deleting old queue")
    try:
        yield
    finally:
        print('Shutting Down.....')
        
# FastAPI app setup
app = FastAPI(lifespan=lifespan)
lock = asyncio.Lock()

# CORS middleware
origins = [
    "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5173", "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware, 
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database and password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
mysql_host = os.getenv("MYSQL_HOST", "mysql")
mysql_user = os.getenv("MYSQL_USER", "root")
mysql_password = os.getenv("MYSQL_PASSWORD", "rootpassword")
mysql_db = os.getenv("MYSQL_DB", "fastapidb")




# Helper function to hash passwords
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# User models for signup and login
class UserSignup(BaseModel):
    username: str
    email: str
    phone: Optional[str] = None
    userRole: str
    password: str

class UserIn(BaseModel):
    email: str
    password: str

# Routes
@app.post("/upload/")
async def upload_resumes(files: List[UploadFile] = File(...)):
    try:
        queue_utils.enqueue_message(message="User Request Added.")
        queue_utils.get_queue_length("User request inserted in queue")
        results = []
        await fetch_data(files[0], results)
        queue_utils.dequeue_message(message="User Request Completed.")
        queue_utils.get_queue_length("One User request complete")
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading resumes: {e}")

def serialize_document(doc):
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc

@app.get("/resumes/")
async def get_resumes():
    try:
        resumes = list(collection.find())
        if not resumes:
            raise HTTPException(status_code=404, detail="No resumes found.")
        return [serialize_document(resume) for resume in resumes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching resumes: {e}")

@app.get("/download-resume", response_class=HTMLResponse)
async def download_resume(format: str = Query("pdf", enum=["pdf", "docx"])):
    try:
        html_content = """
        <html>
            <head><title>Preview Page</title></head>
            <body>
                <h1>Your Preview Page</h1>
                <ul>
                    <li>Name: John Doe</li>
                    <li>Email: johndoe@example.com</li>
                    <li>Occupation: Software Engineer</li>
                </ul>
            </body>
        </html>
        """
        return await create_download_file(format, html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating download file: {str(e)}")

@app.post("/signUp")
async def register(user: UserSignup):
    try:
        create_user = asyncio.create_task(register_user(user))
        return await create_user
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Query failed: {err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "148893426265-gubjmhk6laittlgtm46kckhsehgo7cb6.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/done")
JWT_SECREY_KEY = os.getenv("JWT_SECRET_KEY", "my_secret__key")

flow = Flow.from_client_config(
    {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    },
    scopes=["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", "openid"],
)

@app.get("/auth/google")
def google_login():
    try:
        flow.redirect_uri = REDIRECT_URI
        authorization_url, _ = flow.authorization_url(prompt="consent")
        return RedirectResponse(authorization_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Authentication initiation failed: {str(e)}")

@app.get('/auth/done')
async def get_data(code: str):
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        redirect_response = RedirectResponse("http://localhost:5173/user")
        redirect_response.set_cookie(key="auth_token", value=credentials.id_token, httponly=True, secure=True, samesite="Strict")
        data = google_user_data(credentials.token)
        return redirect_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google authentication failed: {str(e)}")

# JWT validation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.post("/login")
async def login(user: UserIn, response: Response):
    try:
        result = login_user(user)
        response.set_cookie(key="jwt", value=result["bearer_token"], httponly=True, secure=True, samesite="Strict")
        return {"message": "Login successful"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")

@app.get("/protected")
def protected_route(request: Request):
    token = request.cookies.get("jwt")
    auth_token = None
    payload = None
    if token is None:
        auth_token = request.cookies.get("auth_token")
        payload = verify_google(auth_token)
    else:
        payload = verify_token(token)

    if not payload and auth_token is None:
        return {"error": "session fail"}
    
    return {"message": f"Welcome, {payload.get('email')}"}

def verify_google(auth_token):
    id_info = id_token.verify_oauth2_token(auth_token, requests.Request(), GOOGLE_CLIENT_ID)
    return id_info

if __name__ == '__main__':
    uvicorn.run(app, port=9000, host='0.0.0.0')
