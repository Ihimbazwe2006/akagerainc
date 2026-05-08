from fastapi import FastAPI, Depends, HTTPException, Request, status, Form, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional
import stripe
from pydantic import BaseModel
import traceback


# Load environment variables
load_dotenv()
print("🔐 STRIPE SECRET:", os.getenv("STRIPE_SECRET_KEY"))
print("🔓 STRIPE PUBLIC:", os.getenv("STRIPE_PUBLIC_KEY"))

# ==================== DATABASE SETUP (WORKING VERSION) ====================
from database import engine, get_db, Base
from models import User, App, Service, Payment, License
import schemas
from utils import generate_license_key
from admin import admin_router

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Akagera Inc API",
    description="Smart Mobile Solutions API",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://akagerainc.onrender.com", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include admin router
app.include_router(admin_router)


#=======payment

class PaymentIntentRequest(BaseModel):
    amount: float
    service_id: int
    currency: str = "usd"

# ==================== DIRECT DATABASE CONNECTION (FOR APPS) ====================
def get_db_connection():
    """Direct database connection for apps endpoint"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "akagera_inc"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "yves2006"),
            port=os.getenv("DB_PORT", "5432"),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# ==================== HEALTH CHECK ====================
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Akagera Inc API"
    }

# ==================== APPS (WORKING DIRECT CONNECTION) ====================
@app.get("/api/apps", tags=["Apps"])
async def list_apps():
    """Get all available apps - Working version with direct DB connection"""
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, description, short_description, 
                   requires_license, features, how_it_works, 
                   installation_steps, download_url, app_icon, 
                   app_logo, app_image, created_at, updated_at
            FROM apps 
            ORDER BY id
        """)
        
        apps_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        result = []
        for app in apps_data:
            # Parse features if it's JSON string
            features = app.get('features')
            if features and isinstance(features, str):
                try:
                    features = json.loads(features)
                except:
                    features = []
            elif not features:
                features = []
            
            # Parse installation steps if it's JSON string
            installation_steps = app.get('installation_steps')
            if installation_steps and isinstance(installation_steps, str):
                try:
                    installation_steps = json.loads(installation_steps)
                except:
                    installation_steps = []
            elif not installation_steps:
                installation_steps = []
            
            result.append({
                "id": app.get('id'),
                "name": app.get('name'),
                "description": app.get('description'),
                "short_description": app.get('short_description'),
                "requires_license": app.get('requires_license', False),
                "features": features,
                "how_it_works": app.get('how_it_works'),
                "installation_steps": installation_steps,
                "download_url": app.get('download_url'),
                "app_icon": app.get('app_icon'),
                "app_logo": app.get('app_logo'),
                "app_image": app.get('app_image'),
                "created_at": app.get('created_at').isoformat() if app.get('created_at') else None,
                "updated_at": app.get('updated_at').isoformat() if app.get('updated_at') else None
            })
        
        print(f"✅ Returning {len(result)} apps")
        return result
        
    except Exception as e:
        print(f"❌ Error in /api/apps: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/apps/{app_id}", tags=["Apps"])
async def get_app(app_id: int):
    """Get app details by ID - Working version with direct DB connection"""
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, description, short_description, 
                   requires_license, features, how_it_works, 
                   installation_steps, download_url, app_icon, 
                   app_logo, app_image, created_at, updated_at
            FROM apps 
            WHERE id = %s
        """, (app_id,))
        
        app = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not app:
            raise HTTPException(status_code=404, detail="App not found")
        
        # Parse JSON fields
        features = app.get('features')
        if features and isinstance(features, str):
            try:
                features = json.loads(features)
            except:
                features = []
        elif not features:
            features = []
        
        installation_steps = app.get('installation_steps')
        if installation_steps and isinstance(installation_steps, str):
            try:
                installation_steps = json.loads(installation_steps)
            except:
                installation_steps = []
        elif not installation_steps:
            installation_steps = []
        
        return {
            "id": app.get('id'),
            "name": app.get('name'),
            "description": app.get('description'),
            "short_description": app.get('short_description'),
            "requires_license": app.get('requires_license', False),
            "features": features,
            "how_it_works": app.get('how_it_works'),
            "installation_steps": installation_steps,
            "download_url": app.get('download_url'),
            "app_icon": app.get('app_icon'),
            "app_logo": app.get('app_logo'),
            "app_image": app.get('app_image'),
            "created_at": app.get('created_at').isoformat() if app.get('created_at') else None,
            "updated_at": app.get('updated_at').isoformat() if app.get('updated_at') else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in /api/apps/{app_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ==================== USERS (ORIGINAL SQLALCHEMY VERSION) ====================
@app.post("/api/auth/register", response_model=schemas.UserResponse, tags=["Authentication"])
async def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    db_user = User(
        name=user_data.name,
        email=user_data.email,
        google_id=user_data.google_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/auth/google", tags=["Authentication"])
async def google_auth(request: dict, db: Session = Depends(get_db)):
    """Google OAuth authentication"""
    try:
        name = request.get("name", "User")
        email = request.get("email")
        profile_picture = request.get("profile_picture")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            db_user = existing_user
            if profile_picture:
                db_user.profile_picture = profile_picture
            db.commit()
        else:
            db_user = User(
                name=name,
                email=email,
                profile_picture=profile_picture,
                google_id=email
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        
        access_token = f"token_{db_user.id}_{datetime.utcnow().timestamp()}"
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "name": db_user.name,
                "email": db_user.email,
                "profile_picture": db_user.profile_picture,
                "created_at": db_user.created_at.isoformat() if db_user.created_at else None
            }
        }
    except Exception as e:
        print(f"Google auth error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@app.get("/api/users/{user_id}", response_model=schemas.UserResponse, tags=["Users"])
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/api/users/email/{email}", response_model=schemas.UserResponse, tags=["Users"])
async def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """Get user by email"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ==================== SERVICES (SQLALCHEMY VERSION) ====================
@app.get("/api/services", response_model=list[schemas.ServiceResponse], tags=["Services"])
async def list_services(db: Session = Depends(get_db)):
    """Get all available services"""
    services = db.query(Service).all()
    return services

@app.get("/api/services/{service_id}", response_model=schemas.ServiceResponse, tags=["Services"])
async def get_service(service_id: int, db: Session = Depends(get_db)):
    """Get service details by ID"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

# ==================== PAYMENTS ====================
@app.post("/api/payments/create-intent")
async def create_payment_intent(
    request: PaymentIntentRequest,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    stripe_secret = os.getenv("STRIPE_SECRET_KEY")

    # ================= VALIDATE STRIPE CONFIG =================
    if not stripe_secret or stripe_secret.startswith("sk_test_your"):
        raise HTTPException(
            status_code=500,
            detail="Stripe secret key not configured properly in .env"
        )

    stripe.api_key = stripe_secret

    try:
        # ================= VALIDATE USER =================
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ================= VALIDATE AMOUNT =================
        if request.amount is None or request.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid amount")

        # SAFE conversion to cents
        amount_in_cents = int(float(request.amount) * 100)

        # ================= CREATE STRIPE INTENT =================
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency=request.currency.lower(),
            metadata={
                "user_id": str(user_id),
                "service_id": str(request.service_id),
            }
        )

        # ================= SAVE PAYMENT =================
        db_payment = Payment(
            user_id=user_id,
            amount=request.amount,
            currency=request.currency,
            service_id=request.service_id,
            status="pending",
            stripe_transaction_id=intent.id
        )

        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)

        # ================= RESPONSE =================
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "amount": request.amount,
            "currency": request.currency
        }

    except stripe.error.CardError as e:
        print("💳 Stripe Card Error:", str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except stripe.error.StripeError as e:
        print("🔥 Stripe Error:", str(e))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        print("💥 Payment Intent Error:")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal payment error: {str(e)}"
        )

@app.post("/api/payments/webhook", tags=["Payments"])
async def handle_stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events"""
    stripe_secret = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    if not stripe_secret or not webhook_secret:
        raise HTTPException(status_code=400, detail="Stripe webhook not configured")
    
    stripe.api_key = stripe_secret
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        print(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        print(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        
        payment = db.query(Payment).filter(
            Payment.stripe_transaction_id == payment_intent["id"]
        ).first()
        
        if payment:
            payment.status = "completed"
            db.commit()
            
            if payment.service_id:
                license_key = generate_license_key()
                db_license = License(
                    user_id=payment.user_id,
                    license_key=license_key,
                    service_id=payment.service_id,
                    is_active=True,
                    expires_at=datetime.utcnow() + timedelta(days=365)
                )
                db.add(db_license)
                db.commit()
                print(f"License generated for payment {payment.id}: {license_key}")
    
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        
        payment = db.query(Payment).filter(
            Payment.stripe_transaction_id == payment_intent["id"]
        ).first()
        
        if payment:
            payment.status = "failed"
            db.commit()
            print(f"Payment {payment.id} marked as failed")
    
    return {"status": "success", "type": event["type"]}

@app.get("/api/payments/user/{user_id}", response_model=list[schemas.PaymentResponse], tags=["Payments"])
async def get_user_payments(user_id: int, db: Session = Depends(get_db)):
    """Get all payments for a user"""
    payments = db.query(Payment).filter(Payment.user_id == user_id).all()
    return payments

# ==================== LICENSES ====================
@app.get("/api/licenses/user/{user_id}", response_model=list[schemas.LicenseResponse], tags=["Licenses"])
async def get_user_licenses(user_id: int, db: Session = Depends(get_db)):
    """Get all licenses for a user"""
    licenses = db.query(License).filter(License.user_id == user_id).all()
    return licenses

@app.get("/api/licenses/verify/{license_key}", response_model=schemas.LicenseResponse, tags=["Licenses"])
async def verify_license(license_key: str, db: Session = Depends(get_db)):
    """Verify a license key"""
    license = db.query(License).filter(License.license_key == license_key).first()
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    
    if not license.is_active:
        raise HTTPException(status_code=400, detail="License is not active")
    
    if license.expires_at and license.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="License has expired")
    
    return license

@app.post("/api/licenses/generate", response_model=schemas.LicenseKeyResponse, tags=["Licenses"])
async def generate_license(
    user_id: int,
    service_id: int,
    db: Session = Depends(get_db)
):
    """Generate a new license key"""
    license_key = generate_license_key()
    expires_at = datetime.utcnow() + timedelta(days=365)
    
    db_license = License(
        user_id=user_id,
        license_key=license_key,
        service_id=service_id,
        is_active=True,
        expires_at=expires_at
    )
    db.add(db_license)
    db.commit()
    db.refresh(db_license)
    
    return schemas.LicenseKeyResponse(
        license_key=license_key,
        created_at=db_license.created_at,
        expires_at=expires_at,
        message="⚠️ Save this license key securely. You will need it later."
    )

# ==================== STATS ====================
@app.get("/api/stats", response_model=schemas.StatsResponse, tags=["Stats"])
async def get_stats(db: Session = Depends(get_db)):
    """Get application statistics"""
    total_users = db.query(User).count()
    total_payments = db.query(Payment).filter(Payment.status == "completed").count()
    total_apps = db.query(App).count()
    total_revenue = db.query(Payment.amount).filter(Payment.status == "completed").scalar() or 0
    
    return schemas.StatsResponse(
        total_users=total_users,
        total_payments=total_payments,
        total_apps=total_apps,
        total_revenue=total_revenue
    )

# ==================== ROOT ====================
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Akagera Inc API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🚀 FastAPI Server Starting...")
    print("📍 API URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("📱 Apps Endpoint: http://localhost:8000/api/apps")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)