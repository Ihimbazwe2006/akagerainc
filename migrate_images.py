"""
Migration script to update images table to support binary data storage
Run this to update your existing database
"""

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Database connection
try:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://yves:elwg94kBXgrSDcfI2dgwgeyRgJeuEdhv@dpg-d7v324tb910c73akq1s0-a.oregon-postgres.render.com/akagera_inc")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("Adding new columns to images table...")
    
    # Add data column for storing binary image data
    try:
        cursor.execute("""
            ALTER TABLE public.images
            ADD COLUMN IF NOT EXISTS data BYTEA;
        """)
        print("✓ Added 'data' column")
    except Exception as e:
        print(f"! 'data' column might already exist: {e}")
    
    # Add filename column
    try:
        cursor.execute("""
            ALTER TABLE public.images
            ADD COLUMN IF NOT EXISTS filename VARCHAR(255);
        """)
        print("✓ Added 'filename' column")
    except Exception as e:
        print(f"! 'filename' column might already exist: {e}")
    
    # Add mime_type column
    try:
        cursor.execute("""
            ALTER TABLE public.images
            ADD COLUMN IF NOT EXISTS mime_type VARCHAR(50) DEFAULT 'image/jpeg';
        """)
        print("✓ Added 'mime_type' column")
    except Exception as e:
        print(f"! 'mime_type' column might already exist: {e}")
    
    # Make url column nullable
    try:
        cursor.execute("""
            ALTER TABLE public.images
            ALTER COLUMN url DROP NOT NULL;
        """)
        print("✓ Made 'url' column nullable")
    except Exception as e:
        print(f"! Could not update 'url' constraint: {e}")
    
    conn.commit()
    print("\n✅ Migration completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    if conn:
        conn.rollback()
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
