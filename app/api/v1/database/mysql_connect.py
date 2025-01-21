import mysql.connector
import os
from fastapi import HTTPException

mysql_host = os.getenv("MYSQL_HOST", "mysql")
mysql_user = os.getenv("MYSQL_USER", "root")
mysql_password = os.getenv("MYSQL_PASSWORD", "rootpassword")
mysql_db = os.getenv("MYSQL_DB", "fastapidb")



def get_db_connection():
    try:
        return mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            database=mysql_db
        )
        
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {err}")
