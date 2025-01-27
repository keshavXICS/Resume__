from ..database.mysql_connect import get_db_connection
from fastapi import HTTPException
from passlib.context import CryptContext
from ..exception import CustomError

# from ..exception import CustomError
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

# Constants
JWT_SECRET_KEY = "my_secret_key"  # Preferably, use environment variables here
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10

# Initialize password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Helper Functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def select_query(query: str, params: tuple = ()):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        raise CustomError(status_code=500, detail={"error": "Error in select query", "query": query, "message": str(e)})

def check_user_exist(user, cursor):
    query = "SELECT COUNT(*) FROM user_data WHERE email = %s;"
    cursor.execute(query, (user.email,))
    result = cursor.fetchone()
    return result['COUNT(*)'] > 0

def insert_user(user, cursor, conn):
    try:
        hashed_password = hash_password(user.password)
        cursor.execute(
            "INSERT INTO user_data (username, email, phone, password, created_at) VALUES (%s, %s, %s, %s, NOW())",
            (user.username, user.email, user.phone, hashed_password)
        )
        conn.commit()
    except Exception as e:
        raise CustomError(status_code=500, detail=f"Error inserting user data: {e}")

def list_all_users(cursor):
    query = "SELECT * FROM user_data;"
    cursor.execute(query)
    return cursor.fetchall()

# Main Logic Functions
async def register_user(user):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if check_user_exist(user, cursor):
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    insert_user(user, cursor, conn)
    conn.close()
    return {"message": "User registration successful"}

def login_user(user):
    query = "SELECT email, password FROM user_data WHERE email = %s;"
    
    result = select_query(query, (user.email,))
    
    if not result or not verify_password(user.password, result[0]['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    print(1)

    bearer_token = create_access_token(data={"email": user.email})
    return {"bearer_token": bearer_token, "token_type": "bearer"}

# JWT Functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise CustomError(status_code=401, detail="Invalid or expired token")
