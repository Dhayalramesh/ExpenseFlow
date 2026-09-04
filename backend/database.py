from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# ---- Force SQLite ----
DATABASE_URL = "sqlite:///expenseflow.db"

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# ---- Connection ----
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)
Base = declarative_base()

def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()

# ---- Models ----

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    full_name = Column(String(100))
    role = Column(String(20))
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    monthly_limit = Column(Float, default=10000.0)
    
    manager = relationship("User", remote_side=[id], lazy='joined')
    claims = relationship("Claim", foreign_keys="Claim.employee_id", back_populates="employee", lazy='select')

class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"))
    vendor = Column(String(200))
    amount = Column(Float)
    date = Column(Date)
    category = Column(String(50))
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    receipt_fingerprint = Column(String(64), index=True)  # ✅ No unique=True
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    is_duplicate_flagged = Column(Boolean, default=False)
    
    employee = relationship("User", foreign_keys=[employee_id], lazy='joined')
    approver = relationship("User", foreign_keys=[approved_by], lazy='joined')
    payer = relationship("User", foreign_keys=[paid_by], lazy='joined')

    __table_args__ = (
        Index('idx_claims_status_date', 'status', 'date'),
        Index('idx_claims_employee_status', 'employee_id', 'status'),
        Index('idx_claims_fingerprint_date', 'receipt_fingerprint', 'date'),
    )

# ---- IMPORTANT: Drop and recreate tables ----
Base.metadata.drop_all(bind=engine)      # Remove old tables
Base.metadata.create_all(bind=engine)    # Create fresh tables
