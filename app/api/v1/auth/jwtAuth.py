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

from fastapi import HTTPException
from passlib.context import CryptContext

pwd_context =  CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str)->str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str )-> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def userSignUp(user):

    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password  = hash_password(user.password)

    fake_users_db[user.username] = {"username":user.username, "password":hashed_password}
    return fake_users_db


from ..database.mysql_connect import get_db_connection
def select_query(query):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        raise {"error":"Error in select query", "query":query}

def insert_query(query):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        conn.commit()
        conn.close()
        return
    except Exception as e:
        return e