import psycopg2
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

def test_postgres():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'resume_screening'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        print("✅ PostgreSQL connection successful!")
        conn.close()
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")

def test_mongodb():
    try:
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        db = client.resume_documents
        # Test write permission
        db.test.insert_one({'test': 'test'})
        db.test.delete_one({'test': 'test'})
        print("✅ MongoDB connection successful!")
        client.close()
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")

if __name__ == "__main__":
    print("Testing database connections...")
    test_postgres()
    test_mongodb()