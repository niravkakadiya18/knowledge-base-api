
"""
Create admin user with proper password hash for testing
"""

import psycopg2
import hashlib
import secrets

from app.config.settings import settings


def main():
    conn = psycopg2.connect(
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        database=settings.DATABASE_NAME,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
    )

    cur = conn.cursor()

    password = "admin123"
    salt = secrets.token_hex(32)

    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()

    print("Creating admin user...")
    print(f"Password: {password}")
    print(f"Salt: {salt}")
    print(f"Hash: {password_hash}")

    cur.execute("DELETE FROM users WHERE username = 'admin'")

    cur.execute("""
        INSERT INTO users (
            username, email, password_hash, salt,
            full_name, role, client_access, is_active, is_superuser
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, username
    """, (
        'admin',
        'admin@jma.com',
        password_hash,
        salt,
        'System Administrator',
        'super_admin',
        [1, 2, 3],
        True,
        True
    ))

    new_user = cur.fetchone()
    conn.commit()

    print(f"\n✅ Admin user created: ID={new_user[0]}, Username={new_user[1]}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
