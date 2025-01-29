import mysql.connector
import os
from fastapi import HTTPException
from ..exception import CustomError

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
        
        raise CustomError(status_code=500, detail=f"Database connection failed: {err}")

def create_mysql_tables():
    create_resume_map_table = """
    CREATE TABLE IF NOT EXISTS resume_map (
        email VARCHAR(255) NOT NULL,
        mongo_resume_id VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    """
    create_user_data_table = """
    CREATE TABLE IF NOT EXISTS user_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        phone VARCHAR(15),
        password VARCHAR(255) NOT NULL,
        role ENUM('job seeker', 'recruiter') NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(create_resume_map_table)
            cursor.execute(create_user_data_table)
        connection.commit()
        print("Tables `resume_map` and `user_data` ensured in the database.")
    finally:
        connection.close()