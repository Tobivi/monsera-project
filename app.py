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

st.set_page_config(page_title="Monsera V0 Engine", page_icon="⚡", layout="wide")

# --- HELPER: LOAD DATA ---
@st.cache_data
def load_demo_database():
    paths = ["data/consolidated_transactions.csv", "demo/data/consolidated_transactions.csv"]
    for path in paths:
        full_path = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(full_path):
            df = pd.read_csv(full_path)
            if "Transaction_Date" in df.columns:
                df['Transaction_Date'] = pd.to_datetime(df['Transaction_Date'])
            return df
    return None

demo_db = load_demo_database()

# --- SIDEBAR: DATA INSPECTOR & TIME TRAVEL ---
st.sidebar.title("🛠️ Data Inspector")

if demo_db is not None:
    # 1. SHOW DISCOS FOUND
    st.sidebar.markdown("### 🔍 DisCos Found")
    if 'Service_Provider' in demo_db.columns:
        discos = demo_db['Service_Provider'].value_counts()
        st.sidebar.dataframe(discos, use_container_width=True)
    else:
        st.sidebar.error("No 'Service_Provider' column found.")

    # 2. TIME TRAVEL SLIDER (The Fix for Eligibility)
    st.sidebar.markdown("### ⏳ Time Travel")
    st.sidebar.info("Adjust this date to test users from past months.")
    
    min_date = demo_db['Transaction_Date'].min().date()
    max_date = demo_db['Transaction_Date'].max().date()
    
    # Default to the *start* of the dataset to catch the bulk of users? 
    # No, better to default to max, but let user slide back.
    sim_date = st.sidebar.date_input("Simulation 'Today' Date", value=max_date, min_value=min_date, max_value=max_date)
else:
    st.sidebar.warning("Load data to use Inspector.")
    sim_date = datetime.now().date()

# --- MAIN APP ---
st.title("⚡ Monsera V0 Credit Engine")

# --- INPUT SECTION ---
st.subheader("1. Select Customer")

if demo_db is not None:
    # Filter by DisCo first (To solve the "Eko Only" view)
    all_discos = demo_db['Service_Provider'].unique().tolist()
    selected_filter_disco = st.selectbox("Filter by DisCo", ["All"] + all_discos)
    
    if selected_filter_disco != "All":
        filtered_users = demo_db[demo_db['Service_Provider'] == selected_filter_disco]['User_ID'].unique()
    else:
        filtered_users = demo_db['User_ID'].unique()
        
    selected_meter = st.selectbox("Select Meter / User ID", filtered_users)
    
    # Process Selected User
    user_txns = demo_db[demo_db['User_ID'] == selected_meter].sort_values('Transaction_Date', ascending=False)
    
    # PREPARE FOR CALCULATIONS
    # Filter out "Future" transactions based on Time Travel Slider
    user_txns_sim = user_txns[user_txns['Transaction_Date'] <= pd.to_datetime(sim_date)]
    
    if user_txns_sim.empty:
        st.error(f"❌ This user has no transactions before {sim_date}. Try moving the date slider forward.")
    else:
        # Prepare DF for Transformer
        prep_df = user_txns_sim.rename(columns={
            'User_ID': 'Meter No', 
            'Transaction_Date': 'Entry Date',
            'Access_Source': 'User Agent'
        })
        prep_df['is_successful'] = prep_df['Status'].str.upper().isin(['SUCCESS', 'COMPLETED', 'SUCCESSFUL'])
        
        # CALCULATE FEATURES (PASSING THE SIM DATE)
        sim_data = calculate_features(prep_df, reference_date=sim_date)
        
        # RUN SCORING
        results_df = apply_v0_rules(sim_data)
        result = results_df.iloc[0]

        # --- DISPLAY RESULTS ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Selected DisCo", user_txns['Service_Provider'].iloc[0])
        c2.metric("Recency (Days)", int(sim_data['recency_days'].iloc[0]), help="Days since last vend relative to Sim Date")
        c3.metric("Vends (Last 60d)", int(sim_data['vends_60d'].iloc[0]))

        st.subheader(f"2. Decision (as of {sim_date})")
        
        limit = result['Amount_2_Balanced_Growth']
        decision = result['Decision_2_Balanced_Growth']
        
        if decision == "APPROVED":
            st.success(f"✅ **APPROVED: ₦{limit:,.0f}**")
            st.markdown(f"**Score:** {result['Score']} ({result['Band']})")
        else:
            st.error(f"❌ **DECLINED**")
            st.markdown(f"**Reason:** {result['Reason_2_Balanced_Growth']}")
            
            # Debugging Help
            if "dormant" in result['Reason_2_Balanced_Growth'].lower():
                st.caption("💡 **Tip:** This user is dormant. Try dragging the 'Time Travel' slider in the sidebar back to **February 2025**.")
else:
    st.error("Data not found.")