import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.etl.loader import load_and_clean_data
from src.etl.transformer import calculate_features
from src.credit_engine.scoring import apply_v0_rules
from src.credit_engine import config

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Monsera V0 Credit Engine",
    page_icon="⚡",
    layout="wide"
)

# --- SESSION STATE INITIALIZATION ---
if 'demo_stage' not in st.session_state:
    st.session_state.demo_stage = 'INPUT'
if 'context' not in st.session_state:
    st.session_state.context = {}

# --- HELPER: LOAD REAL DATA FOR DEMO ---
@st.cache_data
def load_demo_database():
    """
    Tries to load the consolidated_transactions.csv from the data folder 
    to use as a 'Real User Database' for the demo.
    """
    # Paths to check
    paths = [
        "data/consolidated_transactions.csv",
        "demo/data/consolidated_transactions.csv",
        "../data/consolidated_transactions.csv"
    ]
    
    for path in paths:
        full_path = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(full_path):
            try:
                df = pd.read_csv(full_path)
                # Quick normalization for the demo
                if "Transaction_Date" in df.columns:
                    df['Transaction_Date'] = pd.to_datetime(df['Transaction_Date'])
                return df
            except Exception as e:
                st.error(f"Error loading demo data: {e}")
                return None
    return None

# Load the DB once
demo_db = load_demo_database()

# --- HEADER ---
st.title("⚡ Monsera V0 Credit Engine")
st.markdown("**Behavioral Eligibility & Advance-Sizing Model**")

# --- SIDEBAR ---
st.sidebar.header("Configuration")
app_mode = st.sidebar.radio("Select Interface:", ["Live Transaction Demo", "Batch Portfolio Upload"])
st.sidebar.markdown("---")

# ==========================================
# MODE 1: LIVE TRANSACTION DEMO
# ==========================================
if app_mode == "Live Transaction Demo":
    
    # === STAGE 1: INPUT ===
    if st.session_state.demo_stage == 'INPUT':
        st.subheader("1. Customer & Context")

        # A. MODE SELECTION: REAL VS MANUAL
        input_method = st.radio("Input Method:", 
                                ["Select Existing Customer (Real Data)", "Manual Parameter Entry (Simulation)"], 
                                horizontal=True)

        st.divider()
        
        sim_data = None
        history_df = None
        selected_meter = None
        selected_disco = "Unknown"

        # --- OPTION A: REAL DATA ---
        if input_method == "Select Existing Customer (Real Data)":
            if demo_db is not None:
                # Filter for valid users
                valid_users = demo_db['User_ID'].unique()
                selected_meter = st.selectbox("Search Customer Meter / ID", valid_users)
                
                # Get User Data
                user_txns = demo_db[demo_db['User_ID'] == selected_meter].sort_values('Transaction_Date', ascending=False)
                
                if not user_txns.empty:
                    # 1. Extract DisCo
                    if 'Service_Provider' in user_txns.columns:
                        selected_disco = user_txns['Service_Provider'].iloc[0]
                    
                    # 2. Extract History (Real Transactions)
                    history_df = user_txns[['Transaction_Date', 'Amount', 'Status', 'Service_Provider']].head(5)
                    
                    # 3. Calculate Metrics (Real Time)
                    # We need to map columns to what the transformer expects
                    prep_df = user_txns.rename(columns={
                        'User_ID': 'Meter No', 
                        'Transaction_Date': 'Entry Date',
                        'Access_Source': 'User Agent' # Mapping for device check
                    })
                    # Map status to boolean
                    success_statuses = ['SUCCESS', 'COMPLETED', 'SUCCESSFUL']
                    prep_df['is_successful'] = prep_df['Status'].str.upper().isin(success_statuses)
                    
                    # Run Transformer
                    with st.spinner("Analyzing customer history..."):
                        sim_data = calculate_features(prep_df)
                        
                    # Show Summary
                    st.info(f"Loaded **{len(user_txns)}** transactions for **{selected_meter}**.")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("DisCo", selected_disco)
                    m2.metric("Tenure (Days)", int(sim_data['tenure_days'].iloc[0]))
                    m3.metric("Last Vend", f"{int(sim_data['recency_days'].iloc[0])} days ago")

            else:
                st.warning("⚠️ `consolidated_transactions.csv` not found in /data folder. Please use Manual Entry.")

        # --- OPTION B: MANUAL ENTRY ---
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                selected_meter = st.text_input("Meter No (Simulated)", "SIM_USER_001")
                selected_disco = st.selectbox("DisCo", ["Ikeja Electric", "Eko Electricity", "Abuja Electric", "Enugu Electric"])
            with c2:
                # Sliders for parameters
                tenure = st.number_input("Tenure (Days)", 90)
                vends_60d = st.slider("Vends (Last 60d)", 0, 30, 5)
                recency = st.slider("Days Since Last Vend", 0, 60, 5)
            with c3:
                spend = st.number_input("Median Vend Amount (₦)", 5000)
                fails = st.slider("Failure Rate", 0.0, 1.0, 0.0)
            
            # Construct DataFrame manually
            sim_data = pd.DataFrame({
                'Meter No': [selected_meter],
                'tenure_days': [tenure],
                'vends_60d': [vends_60d],
                'recency_days': [recency],
                'median_vend_amount': [spend],
                'total_success_vends': [15], # Placeholder
                'failure_rate': [fails],
                'volatility': [0.2], # Default
                'unique_devices': [1],
                'avg_monthly_spend': [spend * (vends_60d/2)]
            })
            st.caption("ℹ️ Note: Transaction history is not available for manual simulations.")

        # --- CONTEXT FOR VEND ---
        st.markdown("### 2. Transaction Context")
        xc1, xc2 = st.columns(2)
        with xc1:
            wallet_bal = st.number_input("Current Wallet Balance (₦)", min_value=0, value=200, step=100)
        with xc2:
            request_amt = st.number_input("Electricity Requested (₦)", min_value=1000, value=5000, step=500)

        # --- ACTION ---
        if st.button("🚀 Check Eligibility", type="primary"):
            if sim_data is not None:
                st.session_state.user_persona_data = sim_data
                st.session_state.history_df = history_df # Will be None if Manual
                st.session_state.context = {
                    'wallet': wallet_bal, 
                    'request': request_amt, 
                    'disco': selected_disco, 
                    'meter_id': selected_meter
                }
                st.session_state.demo_stage = 'OFFER'
                st.rerun()

    # === STAGE 2: OFFER REVIEW ===
    elif st.session_state.demo_stage == 'OFFER':
        ctx = st.session_state.context
        
        # 1. Run Scoring
        results_df = apply_v0_rules(st.session_state.user_persona_data)
        result = results_df.iloc[0]
        
        limit = result['Amount_2_Balanced_Growth']
        decision = result['Decision_2_Balanced_Growth']
        
        # 2. Navigation
        st.button("← New Simulation", on_click=lambda: st.session_state.update(demo_stage='INPUT'))
        st.divider()

        # 3. Customer Header
        st.markdown(f"### 👤 Customer: `{ctx['meter_id']}`")
        st.caption(f"Service Provider: **{ctx['disco']}**")

        # 4. REAL HISTORY (Only if it exists)
        if st.session_state.history_df is not None:
            with st.expander("🕒 Recent Transaction History (Real Data)", expanded=False):
                st.dataframe(st.session_state.history_df, use_container_width=True, hide_index=True)

        # 5. The Decision Logic
        total_power = ctx['wallet'] + limit
        credit_needed = max(ctx['request'] - ctx['wallet'], 0)

        # --- SCENARIO A: APPROVED & SUFFICIENT ---
        if decision == "APPROVED" and total_power >= ctx['request']:
            st.success("✅ **Credit Offer Available**")
            
            # Financial Card
            col1, col2, col3 = st.columns(3)
            col1.metric("Wallet Balance", f"₦{ctx['wallet']:,}")
            col2.metric("Credit Limit", f"₦{limit:,.0f}")
            col3.metric("You Pay Now", f"₦{credit_needed:,.0f}", delta="Credit Advance", delta_color="inverse")

            st.info(f"ℹ️ **Repayment:** The ₦{credit_needed:,.0f} credit will be automatically recovered from the next vend on {ctx['disco']}.")
            
            # Acceptance
            c_yes, c_no = st.columns(2)
            if c_yes.button("✅ Accept & Vend", type="primary", use_container_width=True):
                st.session_state.final_result = result
                st.session_state.credit_used = credit_needed
                st.session_state.demo_stage = 'RESULT'
                st.rerun()
            if c_no.button("❌ Decline", use_container_width=True):
                st.session_state.demo_stage = 'INPUT'
                st.rerun()

        # --- SCENARIO B: PARTIAL APPROVAL ---
        elif decision == "APPROVED":
            st.warning(f"⚠️ **Partial Approval**")
            st.write(f"Customer requested **₦{ctx['request']:,}**, but only has **₦{total_power:,.0f}** purchasing power (Wallet + Limit).")
            st.metric("Max Possible Vend", f"₦{total_power:,.0f}")
            st.button("Back", on_click=lambda: st.session_state.update(demo_stage='INPUT'))

        # --- SCENARIO C: DECLINED ---
        else:
            st.error(f"❌ **Credit Declined**")
            st.write(f"**Reason:** {result['Reason_2_Balanced_Growth']}")
            st.button("Back", on_click=lambda: st.session_state.update(demo_stage='INPUT'))

    # === STAGE 3: RECEIPT ===
    elif st.session_state.demo_stage == 'RESULT':
        ctx = st.session_state.context
        used = st.session_state.credit_used
        res = st.session_state.final_result
        
        st.balloons()
        st.success("⚡ **Vend Successful**")
        
        # Receipt UI
        st.markdown("### Transaction Receipt")
        st.markdown(f"""
        | Field | Details |
        | :--- | :--- |
        | **Meter** | `{ctx['meter_id']}` |
        | **DisCo** | {ctx['disco']} |
        | **Total Units** | ₦{ctx['request']:,} |
        | **Credit Used** | ₦{used:,.0f} |
        | **Repayment Due** | Next Vend |
        """)
        
        # Download
        csv_data = pd.DataFrame([{
            "Timestamp": datetime.now(),
            "Meter": ctx['meter_id'],
            "DisCo": ctx['disco'],
            "Amount": ctx['request'],
            "Credit_Used": used,
            "Score": res['Score'],
            "Band": res['Band']
        }]).to_csv(index=False).encode('utf-8')
        
        st.download_button("📥 Download Receipt", csv_data, f"Receipt_{ctx['meter_id']}.csv", "text/csv")
        st.button("Start New Transaction", on_click=lambda: st.session_state.update(demo_stage='INPUT'))

# ==========================================
# MODE 2: BATCH UPLOAD (Preserved)
# ==========================================
elif app_mode == "Batch Portfolio Upload":
    st.header("📂 Bulk Portfolio Analysis")
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv'])
    if uploaded_file:
        try:
            raw_df = load_and_clean_data(uploaded_file)
            if "User_ID" in raw_df.columns: raw_df = raw_df.rename(columns={"User_ID": "Meter No"})
            features_df = calculate_features(raw_df)
            results_df = apply_v0_rules(features_df)
            st.success(f"Processed {len(results_df)} records.")
            st.dataframe(results_df.head())
            st.download_button("📥 Download Results", results_df.to_csv(index=False).encode('utf-8'), "results.csv", "text/csv")
        except Exception as e:
            st.error(f"Error: {e}")