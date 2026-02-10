import psycopg2
import os
from app.config.settings import settings

def init_db():
    try:
        # Connect to the database
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        
        # Read schema file
        print("📖 Reading schema.sql...")
        with open("app/db/schema.sql", "r") as f:
            schema_sql = f.read()
            
        # Execute schema
        print("🚀 Executing schema...")
        cur.execute(schema_sql)
        
        conn.commit()
        print("✅ Database initialized successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        exit(1)

if __name__ == "__main__":
    init_db()
