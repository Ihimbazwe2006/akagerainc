import requests
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Query, Form, Request, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import get_db
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional
import stripe
from pydantic import BaseModel
import traceback

# Load environment variables
load_dotenv()

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
    allow_origins=[
        "https://akagerainc.store",
        "https://akagerainc.onrender.com",
        "http://localhost:3000",
        "http://localhost:8000",
        "*"
    ],
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

# ITEC/AKAGERA INC PAYMENT ENDPOINTS
ITEC_MOMO_API_URL = "https://pay.itecpay.rw/api2/pay"
ITEC_CARD_API_URL = "https://pay.itecpay.rw/api/pay/apis/pesapal/generatecode"
ITEC_VERIFY_API_URL = "https://pay.itecpay.rw/api2/verify"
ITEC_API_KEY = os.getenv("ITEC_API_KEY", "")  # Set your Akagera Inc ITEC API key in env

# USD to RWF conversion
USD_TO_RWF = 1466.52

# Initiate MoMo Payment (ITEC)
class CardPaymentRequest(BaseModel):
    amount: float
    service_id: int
    currency: str = "USD"
    user_id: int
    email: str = None  # Make email optional

class MomoPaymentRequest(BaseModel):
    amount: float
    service_id: int
    currency: str = "USD"
    user_id: int
    phone_number: str
@app.post("/api/payments/initiate-momo")
async def initiate_momo_payment(
    request: MomoPaymentRequest,
    db: Session = Depends(get_db)
):
    if not ITEC_API_KEY:
        raise HTTPException(status_code=500, detail="ITEC API key not configured.")
    
    user = db.query(User).filter(User.id == request.user_id).first()
    service = db.query(Service).filter(Service.id == request.service_id).first()
    
    if not user or not service:
        raise HTTPException(status_code=404, detail="User or service not found.")
    
    amount_rwf = int(round(request.amount * USD_TO_RWF))
    req_ref = str(uuid.uuid4())
    
    payload = {
        "amount": amount_rwf,
        "phone": request.phone_number,
        "key": ITEC_API_KEY,
        "req_ref": req_ref,
        "note": f"AkageraInc Service {request.service_id}",
        "message": f"Payment for {service.name} by {user.email}"
    }
    
    try:
        resp = requests.post(ITEC_MOMO_API_URL, json=payload, timeout=15)
        data = resp.json()
        status_code = data.get("status")
        
        if status_code == 200:
            # Save payment as pending
            db_payment = Payment(
                user_id=request.user_id,
                amount=request.amount,
                currency=request.currency,
                service_id=request.service_id,
                status="pending",
                payment_method="momo",
                stripe_transaction_id=req_ref
            )
            db.add(db_payment)
            db.commit()
            db.refresh(db_payment)
            
            return {
                "success": True, 
                "req_ref": req_ref, 
                "amount_rwf": amount_rwf, 
                "momo_reference": data.get("data", {}).get("transaction_id"),
                "message": "MoMo payment initiated. Awaiting confirmation."
            }
        else:
            error_msg = data.get("data", {}).get("message", "MoMo payment failed.")
            return {"success": False, "error": error_msg}
    except Exception as e:
        print(f"MoMo payment error: {str(e)}")
        return {"success": False, "error": str(e)}

# Initiate Card Payment (ITEC)
@app.post("/api/payments/initiate-card")
async def initiate_card_payment(
    request: CardPaymentRequest,
    db: Session = Depends(get_db)
):
    if not ITEC_API_KEY:
        raise HTTPException(status_code=500, detail="ITEC API key not configured.")
    
    # Get user and service
    user = db.query(User).filter(User.id == request.user_id).first()
    service = db.query(Service).filter(Service.id == request.service_id).first()
    
    if not user or not service:
        raise HTTPException(status_code=404, detail="User or service not found.")
    
    # Use email from request or fallback to user's email
    email = request.email or user.email
    
    amount_rwf = int(round(request.amount * USD_TO_RWF))
    payload = {
        "amount": amount_rwf,
        "email": email,
        "key": ITEC_API_KEY
    }
    
    try:
        resp = requests.post(ITEC_CARD_API_URL, json=payload, timeout=15)
        data = resp.json()
        
        if data.get("status") == 200 and data.get("link"):
            # Save payment as pending
            db_payment = Payment(
                user_id=request.user_id,
                amount=request.amount,
                currency=request.currency,
                service_id=request.service_id,
                status="pending",
                payment_method="card",
                stripe_transaction_id=data.get("PCODE")
            )
            db.add(db_payment)
            db.commit()
            db.refresh(db_payment)
            
            return {
                "success": True, 
                "payment_url": data["link"], 
                "payment_id": data.get("PCODE"), 
                "amount_rwf": amount_rwf
            }
        else:
            return {"success": False, "error": data.get("message", "Card payment failed.")}
    except Exception as e:
        print(f"Card payment error: {str(e)}")
        return {"success": False, "error": str(e)}

# Verify Payment Status (ITEC)
@app.post("/api/payments/status")
async def verify_payment_status(
    req_ref: str = Query(...),
    db: Session = Depends(get_db)
):
    if not ITEC_API_KEY:
        raise HTTPException(status_code=500, detail="ITEC API key not configured.")
    payload = {
        "action": "status_check",
        "req_ref": req_ref,
        "key": ITEC_API_KEY
    }
    try:
        resp = requests.post(ITEC_VERIFY_API_URL, json=payload, timeout=15)
        data = resp.json()
        status = data.get("data", {}).get("status")
        # Update payment status in DB
        db_payment = db.query(Payment).filter(Payment.stripe_transaction_id == req_ref).first()
        if db_payment and status:
            db_payment.status = status.lower()
            db.commit()
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== DIRECT DATABASE CONNECTION (FOR APPS) ====================
def get_db_connection():
    """Direct database connection for apps endpoint"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "oregon-postgres.render.com"),
            database=os.getenv("DB_NAME", "akagera_inc"),
            user=os.getenv("DB_USER", "yves"),
            password=os.getenv("DB_PASSWORD", "elwg94kBXgrSDcfI2dgwgeyRgJeuEdhv"),
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
        for app_data in apps_data:
            # Parse features if it's JSON string
            features = app_data.get('features')
            if features and isinstance(features, str):
                try:
                    features = json.loads(features)
                except:
                    features = []
            elif not features:
                features = []
            
            # Parse installation steps if it's JSON string
            installation_steps = app_data.get('installation_steps')
            if installation_steps and isinstance(installation_steps, str):
                try:
                    installation_steps = json.loads(installation_steps)
                except:
                    installation_steps = []
            elif not installation_steps:
                installation_steps = []
            
            result.append({
                "id": app_data.get('id'),
                "name": app_data.get('name'),
                "description": app_data.get('description'),
                "short_description": app_data.get('short_description'),
                "requires_license": app_data.get('requires_license', False),
                "features": features,
                "how_it_works": app_data.get('how_it_works'),
                "installation_steps": installation_steps,
                "download_url": app_data.get('download_url'),
                "app_icon": app_data.get('app_icon'),
                "app_logo": app_data.get('app_logo'),
                "app_image": app_data.get('app_image'),
                "created_at": app_data.get('created_at').isoformat() if app_data.get('created_at') else None,
                "updated_at": app_data.get('updated_at').isoformat() if app_data.get('updated_at') else None
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
        
        app_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not app_data:
            raise HTTPException(status_code=404, detail="App not found")
        
        # Parse JSON fields
        features = app_data.get('features')
        if features and isinstance(features, str):
            try:
                features = json.loads(features)
            except:
                features = []
        elif not features:
            features = []
        
        installation_steps = app_data.get('installation_steps')
        if installation_steps and isinstance(installation_steps, str):
            try:
                installation_steps = json.loads(installation_steps)
            except:
                installation_steps = []
        elif not installation_steps:
            installation_steps = []
        
        return {
            "id": app_data.get('id'),
            "name": app_data.get('name'),
            "description": app_data.get('description'),
            "short_description": app_data.get('short_description'),
            "requires_license": app_data.get('requires_license', False),
            "features": features,
            "how_it_works": app_data.get('how_it_works'),
            "installation_steps": installation_steps,
            "download_url": app_data.get('download_url'),
            "app_icon": app_data.get('app_icon'),
            "app_logo": app_data.get('app_logo'),
            "app_image": app_data.get('app_image'),
            "created_at": app_data.get('created_at').isoformat() if app_data.get('created_at') else None,
            "updated_at": app_data.get('updated_at').isoformat() if app_data.get('updated_at') else None
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
class PaymentIntentRequest(BaseModel):
    amount: float
    service_id: int
    currency: str = "usd"


class MomoPaymentRequest(BaseModel):
    amount: float
    service_id: int
    currency: str = "usd"
    phone_number: str


def get_usd_to_rwf_rate() -> float:
    # Fixed conversion rate: 1 USD = 1,462 RWF
    return 1462.0


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
            payment_method_types=["card"],
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

@app.post("/api/payments/create-momo-charge")
async def create_momo_charge(
    request: MomoPaymentRequest,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    momo_api_url = os.getenv("MOMO_API_URL")
    momo_api_key = os.getenv("MOMO_API_KEY")
    momo_receiver = os.getenv("MOMO_RECEIVER_NUMBER", "0795226123")

    if not momo_api_url or not momo_api_key:
        raise HTTPException(
            status_code=500,
            detail="MoMo payment processing is not configured. Set MOMO_API_URL and MOMO_API_KEY in environment."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    service = db.query(Service).filter(Service.id == request.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    if request.amount is None or request.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    if not request.phone_number or not request.phone_number.strip():
        raise HTTPException(status_code=400, detail="Phone number is required for MoMo payment")

    exchange_rate = get_usd_to_rwf_rate()
    amount_rwf = int(round(float(request.amount) * exchange_rate))

    payment_payload = {
        "recipient_number": momo_receiver,
        "payer_number": request.phone_number.strip(),
        "amount": amount_rwf,
        "currency": "RWF",
        "description": f"Payment for {service.name} by {user.email}",
        "metadata": {
            "user_id": str(user_id),
            "service_id": str(request.service_id),
            "source": "MoMo"
        }
    }

    headers = {
        "Authorization": f"Bearer {momo_api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(momo_api_url, json=payment_payload, headers=headers, timeout=15)
        response.raise_for_status()
        provider_data = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
        provider_reference = provider_data.get("transaction_id") or provider_data.get("reference") or provider_data.get("id") or ""

        db_payment = Payment(
            user_id=user_id,
            amount=request.amount,
            currency=request.currency,
            service_id=request.service_id,
            status="pending",
            stripe_transaction_id=f"momo:{provider_reference}" if provider_reference else "momo"
        )
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)

        return {
            "status": "pending",
            "amount_usd": request.amount,
            "amount_rwf": amount_rwf,
            "currency": request.currency,
            "momo_number": momo_receiver,
            "reference": provider_reference,
            "message": f"MoMo payment requested for RWF {amount_rwf}. Please complete payment to {momo_receiver}."
        }

    except requests.RequestException as e:
        print(f"MoMo payment request failed: {str(e)}")
        raise HTTPException(status_code=502, detail="Failed to create MoMo payment request. Please try again later.")

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

# ==================== PAYPAL PAYMENT ENDPOINTS ====================
from paypal_service import paypal_service

@app.post("/api/payments/paypal/create-order", tags=["Payments"])
async def create_paypal_order(
    request: PaymentIntentRequest,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """
    Create a PayPal order
    Returns PayPal order ID and approval link for client
    """
    try:
        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate amount
        if request.amount is None or request.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid amount")
        
        # Validate service
        service = db.query(Service).filter(Service.id == request.service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Get frontend URL from environment
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
        # Create PayPal order
        success, paypal_response = paypal_service.create_order(
            amount=str(round(request.amount, 2)),
            currency=request.currency.upper(),
            reference_id=f"order-{user_id}-{datetime.utcnow().timestamp()}",
            description=f"Payment for {service.name}",
            return_url=f"{frontend_url}/payment-success",
            cancel_url=f"{frontend_url}/payment-cancel"
        )
        
        if not success:
            raise HTTPException(status_code=502, detail=paypal_response.get("error", "Failed to create PayPal order"))
        
        paypal_order_id = paypal_response.get("id")
        approval_link = None
        
        # Find PayPal approval link
        for link in paypal_response.get("links", []):
            if link.get("rel") == "approve":
                approval_link = link.get("href")
                break
        
        if not approval_link:
            raise HTTPException(status_code=502, detail="No approval link in PayPal response")
        
        # Save payment to database
        db_payment = Payment(
            user_id=user_id,
            amount=request.amount,
            currency=request.currency,
            service_id=request.service_id,
            status="pending",
            payment_method="paypal",
            paypal_order_id=paypal_order_id
        )
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        
        return {
            "success": True,
            "paypal_order_id": paypal_order_id,
            "approval_url": approval_link,
            "status": "pending",
            "amount": request.amount,
            "currency": request.currency
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"PayPal order creation error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/api/payments/paypal/capture-order", tags=["Payments"])
async def capture_paypal_order(
    paypal_order_id: str = Query(...),
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """
    Capture (complete) a PayPal order after user approval
    Generates license if service requires it
    """
    try:
        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find payment by PayPal order ID
        payment = db.query(Payment).filter(
            Payment.paypal_order_id == paypal_order_id,
            Payment.user_id == user_id
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Capture PayPal order
        success, paypal_response = paypal_service.capture_order(paypal_order_id)
        
        if not success:
            payment.status = "failed"
            db.commit()
            raise HTTPException(status_code=502, detail=paypal_response.get("error", "Failed to capture PayPal order"))
        
        # Check if capture was successful
        status = paypal_response.get("status", "").upper()
        if status != "COMPLETED":
            payment.status = "failed"
            db.commit()
            raise HTTPException(status_code=402, detail=f"PayPal order not completed. Status: {status}")
        
        # Update payment status
        payment.status = "completed"
        db.commit()
        db.refresh(payment)
        
        # Generate license if service requires it
        if payment.service_id:
            service = db.query(Service).filter(Service.id == payment.service_id).first()
            if service:
                license_key = generate_license_key()
                db_license = License(
                    user_id=user_id,
                    license_key=license_key,
                    service_id=payment.service_id,
                    is_active=True,
                    expires_at=datetime.utcnow() + timedelta(days=365)
                )
                db.add(db_license)
                db.commit()
                db.refresh(db_license)
                print(f"License generated for payment {payment.id}: {license_key}")
        
        return {
            "success": True,
            "status": "completed",
            "payment_id": payment.id,
            "message": "Payment completed successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"PayPal order capture error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/payments/paypal/details/{paypal_order_id}", tags=["Payments"])
async def get_paypal_order_details(
    paypal_order_id: str,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get details of a PayPal order"""
    try:
        # Verify payment exists for user
        payment = db.query(Payment).filter(
            Payment.paypal_order_id == paypal_order_id,
            Payment.user_id == user_id
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Get order details from PayPal
        success, paypal_response = paypal_service.get_order_details(paypal_order_id)
        
        if not success:
            raise HTTPException(status_code=502, detail=paypal_response.get("error", "Failed to get PayPal order details"))
        
        return {
            "success": True,
            "paypal_order": paypal_response,
            "payment_status": payment.status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"PayPal order details error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

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