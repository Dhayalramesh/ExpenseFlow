import hashlib
import re
from datetime import datetime, timedelta
from typing import Tuple

def normalize_vendor(vendor: str) -> str:
    """Normalize vendor name for fingerprinting."""
    if not vendor:
        return ""
    vendor = vendor.lower()
    vendor = re.sub(r'\b(inc|llc|ltd|pvt|limited|corp|corporation|co|company|pvt|ltd)\b', '', vendor)
    vendor = re.sub(r'[^\w\s]', '', vendor)
    vendor = re.sub(r'\s+', ' ', vendor).strip()
    return vendor

def generate_fingerprint(vendor: str, amount: float, date: datetime) -> str:
    """Generate a unique fingerprint for a receipt."""
    normalized = normalize_vendor(vendor)
    amount_rounded = round(amount, 2)
    date_str = date.strftime("%Y-%m-%d")
    fingerprint_string = f"{normalized}|{amount_rounded}|{date_str}"
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()

def is_fuzzy_duplicate(
    new_vendor: str,
    new_amount: float,
    new_date: datetime,
    existing_vendor: str,
    existing_amount: float,
    existing_date: datetime
) -> Tuple[bool, float]:
    """Check if two receipts are fuzzy duplicates."""
    date_diff = abs((new_date - existing_date).days)
    if date_diff > 3:
        return False, 0.0
    
    amount_diff = abs(new_amount - existing_amount)
    amount_tolerance = existing_amount * 0.02
    if amount_diff > amount_tolerance:
        return False, 0.0
    
    from difflib import SequenceMatcher
    norm_new = normalize_vendor(new_vendor)
    norm_existing = normalize_vendor(existing_vendor)
    similarity = SequenceMatcher(None, norm_new, norm_existing).ratio()
    
    return similarity > 0.8, similarity