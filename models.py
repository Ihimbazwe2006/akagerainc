from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey, JSON, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    google_id = Column(String(255), unique=True, index=True)
    profile_picture = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    licenses = relationship("License", back_populates="user", cascade="all, delete-orphan")


class App(Base):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    short_description = Column(String(500))
    features = Column(JSON)
    how_it_works = Column(Text)
    installation_steps = Column(JSON)
    requires_license = Column(Boolean, default=False)
    download_url = Column(String(500))
    app_icon = Column(String(500))
    app_logo = Column(String(500))  # App logo for display
    app_image = Column(String(500))  # App banner/cover image
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    licenses = relationship("License", back_populates="app", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="app", cascade="all, delete-orphan")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    icon = Column(String(100))
    image_url = Column(String(500))  # Service background/banner image
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    payments = relationship("Payment", back_populates="service")
    licenses = relationship("License", back_populates="service")
    images = relationship("Image", back_populates="service", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(50), default="pending", index=True)
    stripe_transaction_id = Column(String(255), unique=True)
    service_id = Column(Integer, ForeignKey("services.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="payments")
    service = relationship("Service", back_populates="payments")


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    license_key = Column(String(20), unique=True, index=True, nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"))
    app_id = Column(Integer, ForeignKey("apps.id"))
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="licenses")
    service = relationship("Service", back_populates="licenses")
    app = relationship("App", back_populates="licenses")


class Image(Base):
    """Background and carousel images for pages"""
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500))  # Optional - for external URLs
    data = Column(LargeBinary)  # Store actual image bytes
    filename = Column(String(255))  # Store original filename
    mime_type = Column(String(50), default="image/jpeg")  # image/jpeg, image/png, etc.
    alt_text = Column(String(255))
    page_type = Column(String(50))  # 'home', 'services', 'apps', 'contact', etc.
    app_id = Column(Integer, ForeignKey("apps.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))
    order = Column(Integer, default=0)  # For carousel order
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    app = relationship("App", back_populates="images")
    service = relationship("Service", back_populates="images")
