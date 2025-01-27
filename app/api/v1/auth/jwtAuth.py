from ..exception import CustomError
from fastapi import HTTPException
from passlib.context import CryptContext
from ..database.mysql_connect import get_db_connection

# Set up password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fake user database (for demo purposes)
fake_users_db = {
    "keshav": {
        "username": "keshav",
        "password": "$2b$12$Of1YIfMgQlIfpR40GCdT2uBWkGi59SCAxuc6bnPI.zlTb1D2sG3yC"
    },
    "test1": {
        "username": "test1",
        "password": "$2b$12$Kj.4wxyge/7h4NkfeeK/EuPFdmfalFWz/weyMGUCzBm1WfpSlb0Cq"
    }
}

# Hash password function
def hash_password(password: str) -> str:
    """Hashes a password."""
    return pwd_context.hash(password)

# Verify password function
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

# User sign-up function
async def userSignUp(user):
    """Signs up a new user if the username does not exist."""
    if user.username in fake_users_db:
        raise CustomError(status_code=400, detail="Username already exists")

    # Hash the user's password
    hashed_password = hash_password(user.password)

    # Add the user to the fake database
    fake_users_db[user.username] = {"username": user.username, "password": hashed_password}
    return fake_users_db

# Function to execute a SELECT query
def select_query(query: str):
    """Executes a SELECT query and returns the result."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        raise CustomError(status_code=400, detail=f"Error in SELECT query: {e}")

# Function to execute an INSERT query
def insert_query(query: str):
    """Executes an INSERT query."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        conn.commit()
        conn.close()
    except Exception as e:
        raise CustomError(status_code=400, detail=f"Error in INSERT query: {e}")
