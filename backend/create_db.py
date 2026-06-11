import os
import psycopg
from dotenv import load_dotenv

# Load env variables if they exist
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "lolmht2003")
DB_NAME = os.getenv("DB_NAME", "social_media_automation")

def create_database():
    try:
        # Connect to the default 'postgres' database first with autocommit=True
        conn_str = f"host={DB_HOST} port={DB_PORT} user={DB_USER} password={DB_PASSWORD} dbname=postgres"
        print(f"Connecting to database to check/create '{DB_NAME}'...")
        conn = psycopg.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        # Check if target database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;", (DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database '{DB_NAME}' does not exist. Creating...")
            # Note: Database names cannot be parameterized in SQL, so we use string formatting safely here
            cursor.execute(f"CREATE DATABASE {DB_NAME};")
            print(f"Database '{DB_NAME}' created successfully.")
        else:
            print(f"Database '{DB_NAME}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        print("Please ensure your PostgreSQL database is running and credentials are correct.")

if __name__ == "__main__":
    create_database()
