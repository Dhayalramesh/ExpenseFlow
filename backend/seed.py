from sqlalchemy.orm import Session
from datetime import date, timedelta
import random
from .database import User, Claim
from .crud import create_claim, get_user, clear_user_cache
from .utils import generate_fingerprint

def seed_database(db: Session):
    """Seed the database with realistic data including duplicates."""
    
    # Check if users exist
    if db.query(User).count() > 0:
        return
    
    # ---- Create Users ----
    users = [
        User(username="alice_j", full_name="Alice Johnson", role="staff", monthly_limit=10000),
        User(username="bob_s", full_name="Bob Smith", role="staff", monthly_limit=8000),
        User(username="charlie_b", full_name="Charlie Brown", role="staff", monthly_limit=12000),
        User(username="diana_p", full_name="Diana Prince", role="manager", monthly_limit=15000),
        User(username="eve_a", full_name="Eve Adams", role="staff", monthly_limit=9000),
        User(username="frank_m", full_name="Frank Miller", role="finance", monthly_limit=20000),
        User(username="grace_l", full_name="Grace Lee", role="staff", monthly_limit=7000),
        User(username="henry_w", full_name="Henry Williams", role="staff", monthly_limit=11000),
    ]
    
    for u in users:
        db.add(u)
    db.commit()
    
    # ---- Assign Managers ----
    alice = db.query(User).filter(User.username == "alice_j").first()
    bob = db.query(User).filter(User.username == "bob_s").first()
    charlie = db.query(User).filter(User.username == "charlie_b").first()
    eve = db.query(User).filter(User.username == "eve_a").first()
    grace = db.query(User).filter(User.username == "grace_l").first()
    henry = db.query(User).filter(User.username == "henry_w").first()
    diana = db.query(User).filter(User.username == "diana_p").first()
    
    # Diana manages everyone except Frank (finance)
    for u in [alice, bob, charlie, eve, grace, henry]:
        u.manager_id = diana.id
    db.commit()
    
    # ---- Create Realistic Claims ----
    
    today = date.today()
    
    claims_data = [
        # Alice's claims
        {"vendor": "Starbucks Coffee", "amount": 12.45, "date": today - timedelta(days=5), "category": "meals", "desc": "Morning coffee meeting"},
        {"vendor": "Domino's Pizza", "amount": 24.99, "date": today - timedelta(days=7), "category": "meals", "desc": "Team lunch"},
        {"vendor": "Uber", "amount": 45.00, "date": today - timedelta(days=10), "category": "travel", "desc": "Airport ride"},
        {"vendor": "Amazon", "amount": 89.99, "date": today - timedelta(days=12), "category": "supplies", "desc": "Office supplies"},
        # DUPLICATE of Starbucks (slightly different)
        {"vendor": "Starbucks", "amount": 12.45, "date": today - timedelta(days=3), "category": "meals", "desc": "Coffee"},
        
        # Bob's claims
        {"vendor": "McDonald's", "amount": 8.50, "date": today - timedelta(days=2), "category": "meals", "desc": "Quick lunch"},
        {"vendor": "Ola Cab", "amount": 35.00, "date": today - timedelta(days=6), "category": "travel", "desc": "Client meeting commute"},
        {"vendor": "Office Depot", "amount": 120.00, "date": today - timedelta(days=8), "category": "supplies", "desc": "Printer toner"},
        
        # Charlie's claims (close to limit)
        {"vendor": "The Grand Hotel", "amount": 200.00, "date": today - timedelta(days=1), "category": "lodging", "desc": "Hotel for conference"},
        {"vendor": "Swiggy Food", "amount": 15.75, "date": today - timedelta(days=2), "category": "meals", "desc": "Dinner"},
        {"vendor": "Local Taxi", "amount": 28.00, "date": today - timedelta(days=3), "category": "travel", "desc": "Taxi to office"},
        {"vendor": "Uber Eats", "amount": 22.50, "date": today - timedelta(days=4), "category": "meals", "desc": "Lunch"},
        {"vendor": "Amazon", "amount": 50.00, "date": today - timedelta(days=5), "category": "supplies", "desc": "Stationery"},
        {"vendor": "Starbucks", "amount": 11.00, "date": today - timedelta(days=6), "category": "meals", "desc": "Coffee"},
        {"vendor": "Ola", "amount": 42.00, "date": today - timedelta(days=7), "category": "travel", "desc": "Cab ride"},
        {"vendor": "Zomato", "amount": 18.50, "date": today - timedelta(days=8), "category": "meals", "desc": "Food delivery"},
        # DUPLICATE of Swiggy (same amount, different text)
        {"vendor": "Swiggy", "amount": 15.75, "date": today - timedelta(days=9), "category": "meals", "desc": "Late dinner"},
        
        # Eve's claims
        {"vendor": "Post Office", "amount": 5.50, "date": today - timedelta(days=4), "category": "supplies", "desc": "Postage stamps"},
        {"vendor": "Cafe Coffee Day", "amount": 9.00, "date": today - timedelta(days=5), "category": "meals", "desc": "Coffee"},
        {"vendor": "Train Ticket", "amount": 320.00, "date": today - timedelta(days=9), "category": "travel", "desc": "Train to Delhi"},
        
        # Grace's claims
        {"vendor": "Dunkin' Donuts", "amount": 7.50, "date": today - timedelta(days=3), "category": "meals", "desc": "Breakfast"},
        {"vendor": "Gas Station", "amount": 65.00, "date": today - timedelta(days=6), "category": "travel", "desc": "Fuel"},
        {"vendor": "Walmart", "amount": 45.00, "date": today - timedelta(days=8), "category": "supplies", "desc": "Office supplies"},
        
        # Henry's claims
        {"vendor": "Pizza Hut", "amount": 19.99, "date": today - timedelta(days=2), "category": "meals", "desc": "Team dinner"},
        {"vendor": "Lyft", "amount": 38.00, "date": today - timedelta(days=5), "category": "travel", "desc": "Ride to airport"},
        {"vendor": "Best Buy", "amount": 75.00, "date": today - timedelta(days=7), "category": "supplies", "desc": "Tech supplies"},
    ]
    
    # Map username to user object
    user_map = {u.username: u for u in db.query(User).all()}
    
    # Create claims with various statuses
    for data in claims_data:
        # Assign to a random user
        usernames = ["alice_j", "bob_s", "charlie_b", "eve_a", "grace_l", "henry_w"]
        username = random.choice(usernames)
        user = user_map.get(username)
        if not user:
            continue
        
        claim_date = data["date"]
        status = random.choice(["pending", "approved", "paid"])
        
        fingerprint = generate_fingerprint(data["vendor"], data["amount"], claim_date)
        
        claim = Claim(
            employee_id=user.id,
            vendor=data["vendor"],
            amount=data["amount"],
            date=claim_date,
            category=data["category"],
            description=data["desc"],
            status=status,
            receipt_fingerprint=fingerprint
        )
        db.add(claim)
    
    db.commit()
    clear_user_cache()