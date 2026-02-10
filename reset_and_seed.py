
import psycopg2
import secrets
import hashlib
from app.config.settings import settings

def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(32)
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return password_hash, salt

def reset_and_seed():
    try:
        conn = psycopg2.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
        )
        cur = conn.cursor()
        print("🧹 Cleaning database...")
        
        # Truncate tables with cascade
        tables = ['users', 'clients', 'user_sessions', 'audit_log', 'knowledge_entries', 'stakeholders', 'deliverable_workflows']
        for table in tables:
            cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
            
        print("🌱 Seeding data...")
        
        # 1. Create Default Client (Organisation)
        cur.execute("""
            INSERT INTO clients (name, industry, is_active)
            VALUES (%s, %s, %s)
            RETURNING client_id
        """, ('JMA Global', 'Consulting', True))
        client_id = cur.fetchone()[0]
        print(f"--> Created Org: JMA Global (ID: {client_id})")
        
        # 2. Create Admin: Kaushik
        pwd_hash, salt = hash_password('admin123')
        cur.execute("""
            INSERT INTO users (
                username, email, password_hash, salt,
                full_name, role, client_access, is_active, is_superuser, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id, email
        """, (
            'kaushik',
            'kaushik@jma.com',
            pwd_hash,
            salt,
            'Kaushik (Admin)',
            'super_admin',
            [client_id],
            True,
            True
        ))
        admin = cur.fetchone()
        print(f"--> Created Admin: {admin[1]} (Password: admin123)")
        
        conn.commit()
        print("✅ Database reset and seeded successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()

if __name__ == "__main__":
    reset_and_seed()
