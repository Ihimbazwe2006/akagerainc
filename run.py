import os
import psycopg2
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")

# Path to your SQL file
SQL_FILE = "paypal_migration.sql"


def run_migration():
    try:
        # Connect to database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )

        conn.autocommit = True
        cursor = conn.cursor()

        # Read SQL file
        with open(SQL_FILE, "r", encoding="utf-8") as file:
            sql_script = file.read()

        # Split into individual statements (important for PostgreSQL)
        statements = sql_script.split(";")

        print("🚀 Starting database migration...")

        for i, statement in enumerate(statements):
            stmt = statement.strip()
            if stmt:
                try:
                    cursor.execute(stmt)
                    print(f"✅ Executed statement {i+1}")
                except Exception as e:
                    print(f"⚠️ Error in statement {i+1}: {e}")

        cursor.close()
        conn.close()

        print("🎉 Migration completed successfully!")

    except Exception as e:
        print("❌ Migration failed:", e)


if __name__ == "__main__":
    run_migration()