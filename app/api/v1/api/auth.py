from ..database.mysql_connect import get_db_connection
from fastapi import HTTPException
from passlib.context import CryptContext
import asyncio

pwd_context =  CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str)->str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str )-> bool:
    return pwd_context.verify(plain_password, hashed_password)

def check_user_Exist(user, cursor):
    select_query = f"SELECT COUNT(*) FROM user_data WHERE email = {user.email};"
    cursor.execute(select_query)
    result = cursor.fetchone() 
    if result['COUNT(*)']!=0:
        return True

    return False    


def insert_user(user, cursor, conn):
    try:
        hashed_password = hash_password(user.password)

        cursor.execute(
        "INSERT INTO user_data (username, email, phone, password, created_at) VALUES (%s, %s, %s, %s, NOW())",
        (user.username, user.email, user.phone, hashed_password)
    )
        conn.commit()
        
    except Exception as e:
        raise f"Error in inserting data {e}"

def list_all_users(cursor):
    query = "select * from user_data;"
    cursor.execute(query)  
    return cursor.fetchall()

async def registerUser(user):
    
    conn = asyncio.create_task(get_db_connection())
    conn = await conn 
    cursor = asyncio.current_task(conn.cursor(dictionary=True))
    cursor = await cursor
    if check_user_Exist(user, cursor):
        return HTTPException(status_code=400, detail=f"Email already registered {result['COUNT(*)']}")
 
    insert_user(user, cursor, conn)
    
    result = asyncio.create_task(list_all_users(cursor))
    conn.close()
    result = await result

    return {"data": result}

    

def loginUser(user):
    result=select_query(f"select email, password from user_data where email='{user.email}' and password='{user.password}';")
    if len(result)==0:
        return {"error":"credential mismatch"}
    bearer_token = create_access_token(data={"email":user.email, "password":user.password})
    return {"bearer_token": bearer_token, "token_type":"bearer"}
    # if result[0]['COUNT(*)']==0:
    #     return 'Error: user not exist go to signup'
    # if


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








from datetime import datetime,  timedelta
from jose import JWTError, jwt

JWT_SECREY_KEY = "my_secret__key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1

def create_access_token(data:dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp":expire})
    return jwt.encode(to_encode, JWT_SECREY_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECREY_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None