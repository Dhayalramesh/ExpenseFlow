from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from functools import lru_cache
from .database import User, Claim
from .utils import generate_fingerprint, is_fuzzy_duplicate

# ---- Cached User Lookups ----

@lru_cache(maxsize=128)
def get_user_cached(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user(db: Session, user_id: int) -> Optional[User]:
    return get_user_cached(db, user_id)

def clear_user_cache():
    get_user_cached.cache_clear()

# ---- User Operations ----

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_all_users(db: Session) -> List[User]:
    return db.query(User).all()

def get_team_members(db: Session, manager_id: int) -> List[User]:
    return db.query(User).filter(User.manager_id == manager_id).all()

# ---- Claim Operations ----

def create_claim(
    db: Session,
    employee_id: int,
    vendor: str,
    amount: float,
    claim_date: date,
    category: str,
    description: Optional[str] = None
) -> Claim:
    fingerprint = generate_fingerprint(vendor, amount, claim_date)
    
    claim = Claim(
        employee_id=employee_id,
        vendor=vendor,
        amount=amount,
        date=claim_date,
        category=category,
        description=description,
        receipt_fingerprint=fingerprint,
        status="pending"
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    clear_user_cache()
    return claim

def get_claims_for_user(db: Session, user_id: int, limit: int = 50) -> List[Claim]:
    return db.query(Claim).filter(
        Claim.employee_id == user_id
    ).order_by(Claim.created_at.desc()).limit(limit).all()

def get_claims_for_manager(db: Session, manager_id: int, limit: int = 50) -> List[Claim]:
    team_ids = db.query(User.id).filter(User.manager_id == manager_id).subquery()
    return db.query(Claim).filter(
        Claim.employee_id.in_(team_ids),
        Claim.status == "pending"
    ).order_by(Claim.created_at.asc()).limit(limit).all()

def get_all_claims(db: Session, status: Optional[str] = None, limit: int = 100) -> List[Claim]:
    query = db.query(Claim)
    if status:
        query = query.filter(Claim.status == status)
    return query.order_by(Claim.created_at.desc()).limit(limit).all()

def get_claims_by_status(db: Session, status: str, limit: int = 50) -> List[Claim]:
    return db.query(Claim).filter(
        Claim.status == status
    ).order_by(Claim.created_at.desc()).limit(limit).all()

def approve_claim(db: Session, claim_id: int, approver_id: int) -> Optional[Claim]:
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim or claim.employee_id == approver_id:
        return None
    
    claim.status = "approved"
    claim.approved_by = approver_id
    claim.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(claim)
    return claim

def pay_claim(db: Session, claim_id: int, payer_id: int) -> Optional[Claim]:
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim or claim.status != "approved":
        return None
    
    claim.status = "paid"
    claim.paid_by = payer_id
    claim.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(claim)
    return claim

def reject_claim(db: Session, claim_id: int) -> Optional[Claim]:
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        return None
    claim.status = "rejected"
    db.commit()
    db.refresh(claim)
    return claim

# ---- Optimized Duplicate Detection ----

def check_duplicate(
    db: Session,
    vendor: str,
    amount: float,
    claim_date: date,
    employee_id: Optional[int] = None,
    days_window: int = 30
) -> Dict[str, Any]:
    """Fast duplicate check with limited date window."""
    
    fingerprint = generate_fingerprint(vendor, amount, claim_date)
    
    start_date = claim_date - timedelta(days=days_window)
    end_date = claim_date + timedelta(days=days_window)
    
    query = db.query(Claim).filter(
        Claim.date.between(start_date, end_date),
        Claim.status.in_(["pending", "approved"])
    )
    
    if employee_id:
        query = query.filter(Claim.employee_id == employee_id)
    
    exact = query.filter(Claim.receipt_fingerprint == fingerprint).first()
    if exact:
        return {
            "is_duplicate": True,
            "match_type": "exact",
            "existing_claim": exact,
            "similarity": 1.0
        }
    
    candidates = query.filter(
        Claim.amount.between(amount * 0.85, amount * 1.15)
    ).limit(20).all()
    
    for existing in candidates:
        is_dup, similarity = is_fuzzy_duplicate(
            vendor, amount, claim_date,
            existing.vendor, existing.amount, existing.date
        )
        if is_dup:
            return {
                "is_duplicate": True,
                "match_type": "fuzzy",
                "existing_claim": existing,
                "similarity": similarity
            }
    
    return {
        "is_duplicate": False,
        "match_type": None,
        "existing_claim": None,
        "similarity": 0.0
    }

# ---- Optimized Report ----

def get_monthly_report(db: Session, year: int, month: int) -> Dict[str, Any]:
    """Optimized monthly report using aggregation."""
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    results = db.query(
        Claim.category,
        func.sum(Claim.amount).label('total_amount'),
        func.count(Claim.id).label('count')
    ).filter(
        Claim.status == "paid",
        Claim.date >= start_date,
        Claim.date < end_date
    ).group_by(Claim.category).all()
    
    employee_results = db.query(
        User.full_name,
        func.sum(Claim.amount).label('total_amount')
    ).join(Claim, Claim.employee_id == User.id).filter(
        Claim.status == "paid",
        Claim.date >= start_date,
        Claim.date < end_date
    ).group_by(User.id, User.full_name).all()
    
    category_totals = {r.category: float(r.total_amount) for r in results}
    employee_totals = {r.full_name: float(r.total_amount) for r in employee_results}
    total_spend = sum(category_totals.values())
    claim_count = sum(r.count for r in results)
    
    return {
        "year": year,
        "month": month,
        "total_spend": total_spend,
        "by_category": category_totals,
        "by_employee": employee_totals,
        "claim_count": claim_count
    }