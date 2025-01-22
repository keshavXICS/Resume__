import httpx
from ..database.mysql_connect import get_db_connection
import datetime
import asyncio
import os

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

def google_auth():
    google_auth_url = (
    "https://accounts.google.com/o/oauth2/auth"
    f"?client_id={GOOGLE_CLIENT_ID}"
    "&response_type=code"
    "&redirect_uri=http://localhost:8000/auth/done"
    "&scope=openid email profile"
    )
    return google_auth_url

async def get_token_json(code):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": "http://localhost:8000/auth/done",
        "grant_type": "authorization_code",
    }
    timeout = httpx.Timeout(10.0, connect=10.0)  
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data, timeout=timeout)
        token = response.json()

    if "error" in token:
        return {"error":token}
    
    return token
    
async def get_user_data_json(token):
    user_info_url = "https://openidconnect.googleapis.com/v1/userinfo"
    
    headers = {
        "Authorization": f"Bearer {token['access_token']}"
    }
    timeout = httpx.Timeout(10.0, connect=10.0)  

    async with httpx.AsyncClient() as client:
        response = await client.get(user_info_url, headers=headers, timeout=timeout)

    if response.status_code==200:
        user_info = response.json()
        return user_info
    raise {"error":response}



async def google_user_data(code):
    token = get_token_json(code)
    
    user_info = get_user_data_json(token)
    
    # Check user Exist
    query = f"select count(*) from user_data where email='{user_info.get('email')}';"
    check_user_exist = asyncio.create_task(select_query(query))

    # Expiry time 
    expiry_time=token['expires_in']
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=expiry_time)
    
    # Insert token
    query = f"INSERT INTO user_tokens (email, bearer_token, expiry_time, access_token) VALUES ('{user_info.get('email')}', '{token['id_token']}', '{expiration_time}', '{token['access_token']}');"
    insert_query(query)


    await check_user_exist
    if check_user_exist[0]['count(*)']!=0:
        result = select_query(f"select * from user_data where email = '{user_info.get('email')}';")
        return {"exist":result}
                
    
    query=f"INSERT INTO user_data (username, email, phone, password) VALUES ('{user_info.get('name')}', '{user_info.get('email')}', '77877', 'goodle')"
    insert_query(query)
    result = select_query(f"select * from user_data where email = '{user_info.get('email')}';")

    return  result 
    # else:
    #     raise {"error": "Error while fetching user data from google"}


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