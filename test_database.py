#!/usr/bin/env python
"""
Database test and display script - similar to the reference provided by user
"""
from dotenv import load_dotenv
import os
import json
import psycopg2

# =========================
# LOAD ENVIRONMENT
# =========================
load_dotenv(".env")

DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    DB_URL = "postgresql://postgres:yves2006@localhost:5432/akagera_inc"

print(f"📦 Using Database: {DB_URL}")
print("=" * 60)


# =========================
# DATABASE CONNECTION
# =========================
def get_connection():
    """Create a PostgreSQL connection"""
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"❌ Database Connection Error: {e}")
        raise


# =========================
# DISPLAY APPS
# =========================
def display_apps():
    """Display all apps from the database"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        query = """
        SELECT
            id,
            name,
            description,
            short_description,
            features,
            how_it_works,
            installation_steps,
            requires_license,
            download_url,
            app_icon,
            app_logo,
            app_image,
            created_at
        FROM public.apps
        ORDER BY id DESC;
        """

        cur.execute(query)
        apps = cur.fetchall()

        print(f"\n✅ Found {len(apps)} apps in the database\n")
        print("=" * 60)

        for app in apps:
            print(f"📱 ID: {app[0]}")
            print(f"   Name: {app[1]}")
            print(f"   Description: {app[2]}")
            print(f"   Short Description: {app[3]}")

            # Convert JSON string back to Python list (handle both string and list)
            features = app[4]
            if isinstance(features, str):
                features = json.loads(features) if features else []
            elif features is None:
                features = []
            
            if features:
                print("   Features:")
                for feature in features:
                    print(f"     ✓ {feature}")

            print(f"   How It Works: {app[5]}")

            steps = app[6]
            if isinstance(steps, str):
                steps = json.loads(steps) if steps else []
            elif steps is None:
                steps = []
            
            if steps:
                print("   Installation Steps:")
                for i, step in enumerate(steps, 1):
                    print(f"     {i}. {step}")

            print(f"   Requires License: {'🔒 Yes' if app[7] else '✅ Free'}")
            print(f"   Download URL: {app[8]}")
            print(f"   App Icon: {app[9]}")
            print(f"   App Logo: {app[10]}")
            print(f"   App Image: {app[11]}")
            print(f"   Created At: {app[12]}")
            print("=" * 60)

        cur.close()
        conn.close()

        return len(apps)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0


# =========================
# DISPLAY SERVICES
# =========================
def display_services():
    """Display all services from the database"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        query = """
        SELECT
            id,
            name,
            description,
            price,
            icon,
            image_url,
            created_at
        FROM public.services
        ORDER BY id DESC;
        """

        cur.execute(query)
        services = cur.fetchall()

        print(f"\n✅ Found {len(services)} services in the database\n")
        print("=" * 60)

        for service in services:
            print(f"💼 ID: {service[0]}")
            print(f"   Name: {service[1]}")
            print(f"   Description: {service[2]}")
            print(f"   Price: ${float(service[3]):.2f}")
            print(f"   Icon: {service[4]}")
            print(f"   Image URL: {service[5]}")
            print(f"   Created At: {service[6]}")
            print("=" * 60)

        cur.close()
        conn.close()

        return len(services)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 0


# =========================
# DISPLAY PAYMENTS
# =========================
def display_payments():
    """Display recent payments from the database"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        query = """
        SELECT
            id,
            user_id,
            amount,
            currency,
            status,
            stripe_transaction_id,
            service_id,
            created_at
        FROM public.payments
        ORDER BY created_at DESC
        LIMIT 20;
        """

        cur.execute(query)
        payments = cur.fetchall()

        print(f"\n✅ Found {len(payments)} recent payments\n")
        print("=" * 60)

        for payment in payments:
            status_emoji = "✅" if payment[4] == "completed" else "⏳" if payment[4] == "pending" else "❌"
            print(f"{status_emoji} ID: {payment[0]}")
            print(f"   User ID: {payment[1]}")
            print(f"   Amount: {payment[2]} {payment[3]}")
            print(f"   Status: {payment[4]}")
            print(f"   Stripe ID: {payment[5]}")
            print(f"   Service ID: {payment[6]}")
            print(f"   Created At: {payment[7]}")
            print("=" * 60)

        cur.close()
        conn.close()

        return len(payments)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 0


# =========================
# DISPLAY USERS
# =========================
def display_users():
    """Display all users from the database"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        query = """
        SELECT
            id,
            name,
            email,
            google_id,
            profile_picture,
            created_at
        FROM public.users
        ORDER BY created_at DESC
        LIMIT 20;
        """

        cur.execute(query)
        users = cur.fetchall()

        print(f"\n✅ Found {len(users)} users\n")
        print("=" * 60)

        for user in users:
            print(f"👤 ID: {user[0]}")
            print(f"   Name: {user[1]}")
            print(f"   Email: {user[2]}")
            print(f"   Google ID: {user[3]}")
            print(f"   Profile Picture: {user[4]}")
            print(f"   Created At: {user[5]}")
            print("=" * 60)

        cur.close()
        conn.close()

        return len(users)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 0


# =========================
# RUN MENU
# =========================
def main():
    """Main menu"""
    print("\n" + "=" * 60)
    print("  🗄️  AKAGERA INC - DATABASE VIEWER")
    print("=" * 60 + "\n")

    while True:
        print("\nOptions:")
        print("1. View All Apps")
        print("2. View All Services")
        print("3. View Recent Payments")
        print("4. View All Users")
        print("5. View All Data")
        print("6. Exit")
        print()

        choice = input("Select an option (1-6): ").strip()

        if choice == "1":
            display_apps()
        elif choice == "2":
            display_services()
        elif choice == "3":
            display_payments()
        elif choice == "4":
            display_users()
        elif choice == "5":
            print("\n📊 DISPLAYING ALL DATA")
            print("=" * 60)
            apps_count = display_apps()
            services_count = display_services()
            payments_count = display_payments()
            users_count = display_users()
            print("\n📊 SUMMARY")
            print(f"  Apps: {apps_count}")
            print(f"  Services: {services_count}")
            print(f"  Payments: {payments_count}")
            print(f"  Users: {users_count}")
        elif choice == "6":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Please try again.")


if __name__ == "__main__":
    display_apps()
