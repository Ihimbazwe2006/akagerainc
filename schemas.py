from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# User Schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr


class UserCreate(UserBase):
    google_id: str


class UserResponse(UserBase):
    id: int
    google_id: str
    profile_picture: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# App Schemas
class AppBase(BaseModel):
    name: str
    short_description: Optional[str]
    description: Optional[str]
    requires_license: bool = False
    features: Optional[List[str]]
    how_it_works: Optional[str]
    installation_steps: Optional[List[dict]]
    download_url: Optional[str]
    app_icon: Optional[str]
    app_logo: Optional[str]
    app_image: Optional[str]


class AppCreate(AppBase):
    pass


class AppResponse(AppBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Service Schemas
class ServiceBase(BaseModel):
    name: str
    description: Optional[str]
    price: Decimal = Field(..., decimal_places=2)
    icon: Optional[str]
    image_url: Optional[str]


class ServiceCreate(ServiceBase):
    pass


class ServiceResponse(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Payment Schemas
class PaymentBase(BaseModel):
    amount: Decimal = Field(..., decimal_places=2)
    service_id: Optional[int]


class PaymentCreate(PaymentBase):
    user_id: int


class PaymentResponse(PaymentBase):
    id: int
    user_id: int
    status: str
    stripe_transaction_id: Optional[str]
    currency: str
    created_at: datetime

    class Config:
        from_attributes = True


# License Schemas
class LicenseBase(BaseModel):
    service_id: Optional[int]
    app_id: Optional[int]


class LicenseCreate(LicenseBase):
    user_id: int


class LicenseResponse(LicenseBase):
    id: int
    user_id: int
    license_key: str
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Payment Intent Schemas
class CreatePaymentIntentRequest(BaseModel):
    amount: Decimal
    service_id: int
    currency: str = "USD"


class CreatePaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
    amount: Decimal
    currency: str


# License Key Response
class LicenseKeyResponse(BaseModel):
    license_key: str
    created_at: datetime
    expires_at: Optional[datetime]
    message: str


# Google OAuth Schemas
class GoogleAuthRequest(BaseModel):
    token: str


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str


# Error Response
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# Stats Schemas
class StatsResponse(BaseModel):
    total_users: int
    total_payments: int
    total_apps: int
    total_revenue: Decimal


# Image Schemas
class ImageBase(BaseModel):
    url: str
    alt_text: Optional[str]
    page_type: Optional[str]
    app_id: Optional[int]
    service_id: Optional[int]
    order: int = 0
    is_active: bool = True


class ImageCreate(ImageBase):
    pass


class ImageResponse(ImageBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
