import os
import httpx
import datetime
import asyncio
from ..exception import CustomError
from ..database.mysql_connect import get_db_connection

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "148893426265-gubjmhk6laittlgtm46kckhsehgo7cb6.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/done")
JWT_SECREY_KEY = os.getenv("JWT_SECRET_KEY", "my_secret__key")

# Generate Google Auth URL
# def google_auth():
#     try:
#         google_auth_url = (
#             "https://accounts.google.com/o/oauth2/auth"
#             f"?client_id={GOOGLE_CLIENT_ID}"
#             "&response_type=code"
#             "&redirect_uri=http:/localhost:5173/user"
#             "&scope=openid email profile"
#         )
#         return google_auth_url
#     except Exception as e:
#         write_log(f"Google Auth error: {e}")
#         return {"error": "Google Auth fail"}

# Function to get token from Google
async def get_token_json(code: str) -> dict:
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": "http://localhost:8000/auth/done",
        "grant_type": "authorization_code",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    timeout = httpx.Timeout(10.0, connect=10.0)
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data, headers=headers, timeout=timeout)
        token = response.json()
    
    if "error" in token:
        write_log(f"Token retrieval failed: {token}")
        return {"error": token}

    return token

# Function to get user data from Google
async def get_user_data_json(token: dict) -> dict:
    # user_info_url = "https://openidconnect.googleapis.com/v2/userinfo"
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {
        "Authorization": f"Bearer {token['access_token']}"
    }
    timeout = httpx.Timeout(10.0, connect=10.0)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(user_info_url, headers=headers, timeout=timeout)
    
    if response.status_code == 200:
        return response.json()
    
    write_log(f"Error fetching user info: {response.json()}")
    raise CustomError(status_code=400, detail="Failed to fetch user data from Google")

# Main function to handle Google user data
async def google_user_data(token: str):
    # token = await get_token_json(code)

    if "error" in token:
        return token
    user_info = await get_user_data_json(token)
    # Check if the user exists in the database
    query = f"SELECT COUNT(*) FROM user_data WHERE email='{user_info.get('email')}';"
    check_user_exist = select_query(query)
    # check_user_exist = await check_user_exist

    # Calculate expiration time
    expiry_time = token['expires_in']
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=expiry_time)


    query = f"REPLACE INTO user_tokens (email, bearer_token, expiry_time, access_token) VALUES ('{user_info.get('email')}', '{token['id_token']}', '{expiration_time}', '{token['access_token']}');"
    insert_query(query)
    # Wait for the user existence check to complete
    if check_user_exist[0]['COUNT(*)'] != 0:
        result = select_query(f"SELECT * FROM user_data WHERE email='{user_info.get('email')}';")
        return {"exist": result}

    # Insert the new user if not exists
    query = f"INSERT INTO user_data (username, email, phone, password) VALUES ('{user_info.get('name')}', '{user_info.get('email')}', '77877', 'google')"
    insert_query(query)
    
    result = select_query(f"SELECT * FROM user_data WHERE email='{user_info.get('email')}';")
    return result

# Execute select queries
def select_query(query: str) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        write_log(f"Error executing select query: {e}")
        raise CustomError(status_code=400, detail="Error in select query")

# Insert query function
def insert_query(query):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        conn.commit()
        conn.close()
    except Exception as e:
        write_log(f"Error executing insert query: {e}")
        raise CustomError(status_code=400, detail="Error in insert query")

# Helper function for logging errors
def write_log(message: str):
    with open("log.txt", "a") as log_file:
        log_file.write(f"{message}\n")
