import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date
import time

from backend.database import get_db, db_session
from backend.crud import *
from backend.ai_parser import parse_receipt
from backend.seed import seed_database

# ---- Page Config ----
st.set_page_config(
    page_title="ExpenseFlow - Smart Expense Management",
    page_icon="💰",
    layout="wide"
)

# ---- Session State ----
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "parsed_receipt" not in st.session_state:
    st.session_state.parsed_receipt = None

# ---- Initialize Database ----
db = next(get_db())
seed_database(db)
db.close()

# ---- Cache Functions ----

@st.cache_data(ttl=30, show_spinner=False)
def get_cached_claims(user_id: int, role: str, manager_id: int = None):
    """Cache claims data for 30 seconds."""
    db = next(get_db())
    try:
        if role == "staff":
            return get_claims_for_user(db, user_id)
        elif role == "manager":
            return get_claims_for_manager(db, manager_id)
        else:
            return get_all_claims(db)
    finally:
        db.close()

@st.cache_data(ttl=120, show_spinner=False)
def get_cached_report(year: int, month: int):
    """Cache monthly report for 2 minutes."""
    db = next(get_db())
    try:
        return get_monthly_report(db, year, month)
    finally:
        db.close()

@st.cache_data(ttl=60, show_spinner=False)
def get_cached_users():
    """Cache user list for 1 minute."""
    db = next(get_db())
    try:
        return get_all_users(db)
    finally:
        db.close()

# ---- Login Section ----

def login_section():
    st.sidebar.title("🔐 ExpenseFlow")
    st.sidebar.caption("Smart Expense Management")
    
    users = get_cached_users()
    user_options = {f"{u.full_name} ({u.role.upper()})": u.id for u in users}
    
    selected = st.sidebar.selectbox(
        "Select User",
        options=list(user_options.keys()),
        index=0
    )
    
    if st.sidebar.button("🔑 Login", type="primary", use_container_width=True):
        user_id = user_options[selected]
        db = next(get_db())
        try:
            user = get_user(db, user_id)
            st.session_state.user = user
            st.session_state.role = user.role
            st.rerun()
        finally:
            db.close()
    
    st.sidebar.divider()
    st.sidebar.caption("👥 Demo Users: Staff, Manager, Finance")
    st.sidebar.caption("💡 Try submitting duplicate receipts!")

# ---- Staff Dashboard ----

def staff_dashboard(user):
    st.header("📋 My Claims")
    
    # ---- Submit Claim ----
    with st.expander("➕ Submit New Claim", expanded=False):
        st.subheader("📸 Upload or Paste Receipt")
        
        col1, col2 = st.columns(2)
        
        with col1:
            receipt_text = st.text_area(
                "Paste receipt text",
                height=100,
                placeholder="Paste the receipt text here...",
                key="staff_text"
            )
        
        with col2:
            uploaded_file = st.file_uploader(
                "Or upload a receipt image",
                type=["jpg", "jpeg", "png"],
                key="staff_upload"
            )
        
        if st.button("🔍 Parse Receipt", type="secondary"):
            if receipt_text or uploaded_file:
                with st.spinner("Parsing receipt..."):
                    image_bytes = uploaded_file.read() if uploaded_file else None
                    result = parse_receipt(
                        text=receipt_text if receipt_text else None,
                        image_bytes=image_bytes
                    )
                    
                    if result.get("error"):
                        st.error(f"❌ {result['error']}")
                    else:
                        st.session_state.parsed_receipt = result
                        st.success(f"✅ Parsed! Confidence: {result['confidence']*100:.0f}%")
            else:
                st.warning("Please provide receipt text or upload an image.")
        
        # Show parsed result
        if st.session_state.parsed_receipt:
            parsed = st.session_state.parsed_receipt
            
            st.subheader("📝 Review Extracted Data")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                vendor = st.text_input("Vendor *", value=parsed.get("vendor") or "")
                amount = st.number_input(
                    "Amount (₹) *",
                    value=float(parsed.get("amount") or 0.0),
                    min_value=0.0,
                    step=1.0
                )
            
            with col2:
                claim_date = st.date_input(
                    "Date *",
                    value=datetime.strptime(parsed.get("date"), "%Y-%m-%d").date() 
                    if parsed.get("date") else date.today()
                )
                categories = ["meals", "travel", "lodging", "supplies", "software", "other"]
                default_cat = parsed.get("category", "other")
                category = st.selectbox(
                    "Category *",
                    options=categories,
                    index=categories.index(default_cat) if default_cat in categories else 5
                )
            
            with col3:
                description = st.text_area("Description", value=parsed.get("description") or "", height=68)
                st.caption(f"Confidence: {parsed.get('confidence', 0)*100:.0f}%")
            
            # ---- Duplicate Check ----
            duplicate_result = None
            submit_disabled = False
            
            if vendor and amount > 0:
                db = next(get_db())
                try:
                    duplicate_result = check_duplicate(db, vendor, amount, claim_date, user.id)
                finally:
                    db.close()
                
                if duplicate_result and duplicate_result["is_duplicate"]:
                    existing = duplicate_result["existing_claim"]
                    match_type = duplicate_result["match_type"]
                    
                    if match_type == "exact":
                        st.error(
                            f"🚫 **EXACT DUPLICATE DETECTED!**\n\n"
                            f"This receipt was already claimed on {existing.date.strftime('%Y-%m-%d')} "
                            f"for ₹{existing.amount:.2f}.\n\n"
                            f"**Submission blocked.**"
                        )
                        submit_disabled = True
                    else:
                        st.warning(
                            f"⚠️ **Possible duplicate detected** ({match_type} match, "
                            f"{duplicate_result['similarity']*100:.0f}% similar).\n\n"
                            f"Previously claimed on {existing.date.strftime('%Y-%m-%d')} "
                            f"for ₹{existing.amount:.2f}."
                        )
                        submit_disabled = False
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("📤 Submit Claim", disabled=submit_disabled, type="primary"):
                    if vendor and amount > 0:
                        db = next(get_db())
                        try:
                            claim = create_claim(
                                db, user.id, vendor, amount, claim_date, category, description
                            )
                            st.success(f"✅ **Claim #{claim.id} submitted successfully!**")
                            st.session_state.parsed_receipt = None
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        finally:
                            db.close()
                    else:
                        st.error("Please fill in all required fields (*).")
    
    # ---- My Claims Table ----
    st.subheader("📋 Claim History")
    
    my_claims = get_cached_claims(user.id, "staff")
    
    if my_claims:
        df = pd.DataFrame([{
            "ID": c.id,
            "Vendor": c.vendor,
            "Amount": f"₹{c.amount:,.2f}",
            "Date": c.date.strftime("%Y-%m-%d"),
            "Category": c.category.title(),
            "Status": c.status.upper()
        } for c in my_claims])
        
        status_colors = {"PENDING": "🟡", "APPROVED": "🟢", "PAID": "🔵", "REJECTED": "🔴"}
        df["Status"] = df["Status"].apply(lambda x: f"{status_colors.get(x, '⚪')} {x}")
        
        st.dataframe(df, use_container_width=True, hide_index=True, height=300)
        
        # Stats
        col1, col2, col3 = st.columns(3)
        pending = sum(1 for c in my_claims if c.status == "pending")
        approved = sum(1 for c in my_claims if c.status == "approved")
        total = sum(c.amount for c in my_claims if c.status == "paid")
        
        col1.metric("📌 Pending", pending)
        col2.metric("✅ Approved", approved)
        col3.metric("💰 Total Paid", f"₹{total:,.2f}")
    else:
        st.info("📭 No claims yet. Submit your first claim above!")

# ---- Manager Dashboard ----

def manager_dashboard(user):
    st.header("👥 Team Claims")
    
    db = next(get_db())
    try:
        team = get_team_members(db, user.id)
        st.caption(f"Managing {len(team)} team members")
    finally:
        db.close()
    
    # ---- Pending Approvals ----
    st.subheader("📌 Pending Approvals")
    
    pending_claims = get_cached_claims(user.id, "manager", user.id)
    
    if pending_claims:
        for claim in pending_claims:
            db = next(get_db())
            try:
                employee = get_user(db, claim.employee_id)
            finally:
                db.close()
            
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.markdown(f"**🏢 {claim.vendor}**")
                    st.caption(f"👤 {employee.full_name} | 📅 {claim.date.strftime('%Y-%m-%d')}")
                    if claim.description:
                        st.caption(f"📝 {claim.description}")
                
                with col2:
                    st.markdown(f"**₹{claim.amount:,.2f}**")
                    st.caption(f"📂 {claim.category.title()}")
                
                with col3:
                    if claim.employee_id == user.id:
                        st.warning("⚠️ Cannot self-approve")
                    else:
                        if st.button(f"✅ Approve #{claim.id}", key=f"approve_{claim.id}"):
                            db = next(get_db())
                            try:
                                approved = approve_claim(db, claim.id, user.id)
                                if approved:
                                    st.success(f"✅ Claim #{claim.id} approved!")
                                    st.cache_data.clear()
                                    time.sleep(0.5)
                                    st.rerun()
                            finally:
                                db.close()
                
                with col4:
                    if st.button(f"❌ Reject #{claim.id}", key=f"reject_{claim.id}"):
                        db = next(get_db())
                        try:
                            rejected = reject_claim(db, claim.id)
                            if rejected:
                                st.warning(f"❌ Claim #{claim.id} rejected.")
                                st.cache_data.clear()
                                time.sleep(0.5)
                                st.rerun()
                        finally:
                            db.close()
    else:
        st.info("✅ No pending claims from your team!")
    
    # ---- Team Spending ----
    st.subheader("📊 Team Spending Overview")
    
    db = next(get_db())
    try:
        team_ids = [t.id for t in team]
        all_team_claims = db.query(Claim).filter(Claim.employee_id.in_(team_ids)).all()
    finally:
        db.close()
    
    if all_team_claims:
        df = pd.DataFrame([{
            "Employee": get_user(db, c.employee_id).full_name,
            "Amount": c.amount,
            "Category": c.category.title(),
            "Status": c.status.upper(),
            "Date": c.date.strftime("%Y-%m-%d")
        } for c in all_team_claims])
        
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("Employee:N", title="Employee"),
            y=alt.Y("sum(Amount):Q", title="Total Spend (₹)"),
            color="Category:N",
            tooltip=["Employee", "sum(Amount)", "Category"]
        ).properties(height=300)
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No team spending data yet.")

# ---- Finance Dashboard ----

def finance_dashboard(user):
    st.header("💰 Finance Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["📋 All Claims", "✅ Pay Claims", "📊 Monthly Report"])
    
    # ---- Tab 1: All Claims ----
    with tab1:
        all_claims = get_cached_claims(None, "finance")
        
        if all_claims:
            db = next(get_db())
            try:
                df = pd.DataFrame([{
                    "ID": c.id,
                    "Employee": get_user(db, c.employee_id).full_name,
                    "Vendor": c.vendor,
                    "Amount": f"₹{c.amount:,.2f}",
                    "Date": c.date.strftime("%Y-%m-%d"),
                    "Category": c.category.title(),
                    "Status": c.status.upper()
                } for c in all_claims])
            finally:
                db.close()
            
            status_colors = {"PENDING": "🟡", "APPROVED": "🟢", "PAID": "🔵", "REJECTED": "🔴"}
            df["Status"] = df["Status"].apply(lambda x: f"{status_colors.get(x, '⚪')} {x}")
            
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("No claims in the system.")
    
    # ---- Tab 2: Pay Claims ----
    with tab2:
        db = next(get_db())
        try:
            approved_claims = get_claims_by_status(db, "approved", limit=50)
        finally:
            db.close()
        
        if approved_claims:
            st.subheader(f"💳 Ready to Pay ({len(approved_claims)})")
            
            for claim in approved_claims:
                db = next(get_db())
                try:
                    employee = get_user(db, claim.employee_id)
                finally:
                    db.close()
                
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**🏢 {claim.vendor}**")
                        st.caption(f"👤 {employee.full_name} | 📅 {claim.date.strftime('%Y-%m-%d')}")
                    
                    with col2:
                        st.markdown(f"**₹{claim.amount:,.2f}**")
                        st.caption(f"📂 {claim.category.title()}")
                    
                    with col3:
                        if st.button(f"💳 Pay #{claim.id}", key=f"pay_{claim.id}", type="primary"):
                            db = next(get_db())
                            try:
                                paid = pay_claim(db, claim.id, user.id)
                                if paid:
                                    st.success(f"✅ Claim #{claim.id} marked as paid!")
                                    st.cache_data.clear()
                                    time.sleep(0.5)
                                    st.rerun()
                            finally:
                                db.close()
        else:
            st.info("✅ No approved claims waiting for payment.")
    
    # ---- Tab 3: Monthly Report ----
    with tab3:
        st.subheader("📊 Monthly Spend Report")
        
        col1, col2 = st.columns(2)
        with col1:
            report_year = st.number_input("Year", min_value=2020, max_value=2030, value=date.today().year)
        with col2:
            report_month = st.selectbox("Month", options=range(1, 13), index=date.today().month - 1)
        
        if st.button("📈 Generate Report", type="primary"):
            report = get_cached_report(report_year, report_month)
            
            st.metric("Total Spend", f"₹{report['total_spend']:,.2f}", f"{report['claim_count']} claims")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if report['by_category']:
                    cat_df = pd.DataFrame([
                        {"Category": k.title(), "Amount": v} for k, v in report['by_category'].items()
                    ])
                    
                    chart = alt.Chart(cat_df).mark_bar().encode(
                        x=alt.X("Category:N", sort="-y"),
                        y=alt.Y("Amount:Q", title="Amount (₹)"),
                        color="Category:N",
                        tooltip=["Category", "Amount"]
                    ).properties(height=300)
                    
                    st.altair_chart(chart, use_container_width=True)
            
            with col2:
                if report['by_employee']:
                    emp_df = pd.DataFrame([
                        {"Employee": k, "Amount": v} for k, v in report['by_employee'].items()
                    ]).sort_values("Amount", ascending=False)
                    
                    st.dataframe(
                        emp_df.assign(Amount=emp_df["Amount"].apply(lambda x: f"₹{x:,.2f}")),
                        use_container_width=True,
                        hide_index=True,
                        height=300
                    )

# ---- Main App ----

def main():
    if st.session_state.user is None:
        login_section()
        return
    
    user = st.session_state.user
    role = st.session_state.role
    
    # Sidebar
    st.sidebar.title("💰 ExpenseFlow")
    st.sidebar.success(f"👤 **{user.full_name}**")
    st.sidebar.caption(f"Role: {role.upper()} | Limit: ₹{user.monthly_limit:,.0f}")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.parsed_receipt = None
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.divider()
    st.sidebar.caption("💡 **Tips:**")
    st.sidebar.caption("• Try submitting duplicate receipts")
    st.sidebar.caption("• Managers cannot self-approve")
    st.sidebar.caption("• Finance can see monthly reports")
    
    # Route to appropriate dashboard
    if role == "staff":
        staff_dashboard(user)
    elif role == "manager":
        manager_dashboard(user)
    elif role == "finance":
        finance_dashboard(user)
    else:
        st.error("Unknown role. Please login again.")

if __name__ == "__main__":
    main()