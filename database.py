from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('DB_USER', 'yves')}:{os.getenv('DB_PASSWORD', 'elwg94kBXgrSDcfI2dgwgeyRgJeuEdhv')}@"
    f"{os.getenv('DB_HOST', 'oregon-postgres.render.com')}:{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'akagera_inc')}"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=os.getenv("DEBUG", "False") == "True"
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
