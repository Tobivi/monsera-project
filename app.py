import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
from datetime import timedelta

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.etl.loader import load_and_clean_data
from src.etl.transformer import calculate_features
from src.credit_engine.scoring import apply_v0_rules
from src.credit_engine import config

# --- PAGE CONFIG ---
st.set_page_config(page_title="Monsera V0 Credit Demo", layout="wide")

st.title("⚡ Monsera V0 Credit Engine")
st.markdown("""
**Stakeholder Demo Console:** Analyze real customer behavior, simulate credit requests, and audit portfolio performance.
""")

# --- HELPER: LOAD REAL DATA ---
@st.cache_data
def load_db():
    # Try to load the consolidated data for the demo
    path = os.path.join(os.path.dirname(__file__), "data", "consolidated_transactions.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        # Standardize Date
        df["Transaction_Date"] = pd.to_datetime(df["Transaction_Date"])
        # Standardize Status
        df["Status"] = df["Status"].str.upper()
        return df
    return None

db_df = load_db()

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("Configuration")

# Mode Selection
options = ["Live Customer Demo", "Manual Profile Builder", "Batch Portfolio Analysis"]
app_mode = st.sidebar.radio("Select Operation Mode:", options)

st.sidebar.markdown("---")
st.sidebar.header("Active Scenarios")

def display_scenario_params(name, params):
    with st.sidebar.expander(f"⚙️ {name}"):
        st.caption(f"Min Vends (60d): **{params['min_vends_60d']}**")
        st.caption(f"Max Dormancy: **{params['max_dormancy_days']} days**")
        st.caption(f"Limit Strategy: **{params['limit_strategy']}**")
        st.caption(f"Multipliers: {params['multipliers']}")

for name, params in config.SCENARIOS.items():
    display_scenario_params(name, params)

# ==========================================
# MODE 1: LIVE CUSTOMER DEMO (New Feature)
# ==========================================
if app_mode == "Live Customer Demo":
    if db_df is None:
        st.error("⚠️ 'data/consolidated_transactions.csv' not found. Please upload data or use Manual Mode.")
    else:
        st.subheader("1. Select Customer")
        
        # 1. Filter by DisCo
        discos = db_df["Service_Provider"].unique()
        selected_disco = st.selectbox("Filter by DisCo:", discos, index=0)
        
        # 2. Select User
        disco_users = db_df[db_df["Service_Provider"] == selected_disco]["User_ID"].unique()
        selected_user = st.selectbox("Search Meter / User ID:", disco_users)

        # 3. Get User History
        user_history = db_df[db_df["User_ID"] == selected_user].sort_values("Transaction_Date")
        
        # Display Header Info
        c1, c2, c3 = st.columns(3)
        c1.metric("Meter ID", selected_user)
        c2.metric("DisCo", selected_disco)
        c3.metric("Total History", f"{len(user_history)} transactions")

        st.markdown("### 📜 Recent Transaction History")
        st.dataframe(
            user_history.tail(5)[["Transaction_Date", "Amount", "Status", "Access_Source", "Is_Retry"]].sort_values("Transaction_Date", ascending=False),
            use_container_width=True
        )

        # 4. Calculate Features (Live)
        # We assume the 'transformer.py' logic, but we do it for a single user here to bridge the gap
        # Or ideally, we reuse calculate_features if it handles single groups well. 
        # For safety/speed in demo, we calculate the exact props needed by the engine.
        
        SUCCESS_STATUSES = {"SUCCESS", "SUCCESSFUL", "COMPLETED"}
        
        today = user_history["Transaction_Date"].max()
        cutoff_60d = today - timedelta(days=60)
        
        # Filter sets
        success_all = user_history[user_history["Status"].isin(SUCCESS_STATUSES)]
        success_60d = success_all[success_all["Transaction_Date"] >= cutoff_60d]
        recent_attempts = user_history[user_history["Transaction_Date"] >= cutoff_60d]
        
        # Metrics
        if not success_all.empty:
            tenure = (today - success_all["Transaction_Date"].min()).days
            recency = (today - success_all["Transaction_Date"].max()).days
            median_vend = success_all["Amount"].median()
            volatility = success_all["Amount"].std() / median_vend if len(success_all) > 1 and median_vend > 0 else 0
        else:
            tenure, recency, median_vend, volatility = 0, 999, 0, 0
            
        vends_60d = len(success_60d)
        total_vends = len(success_all)
        
        # Failure Rate (Last 60 days)
        failed_count = len(recent_attempts) - len(success_60d)
        failure_rate = failed_count / len(recent_attempts) if len(recent_attempts) > 0 else 0.0
        
        # Unique Devices (Proxy via Access_Source or default to 1 if missing)
        unique_devices = user_history["Access_Source"].nunique() if "Access_Source" in user_history.columns else 1
        avg_monthly = median_vend * (vends_60d / 2) if vends_60d > 0 else 0

        # Construct DF for Engine
        sim_df = pd.DataFrame([{
            'Meter No': selected_user,
            'tenure_days': tenure,
            'vends_60d': vends_60d,
            'recency_days': recency,
            'median_vend_amount': median_vend,
            'total_success_vends': total_vends,
            'failure_rate': failure_rate,
            'volatility': volatility,
            'unique_devices': unique_devices,
            'avg_monthly_spend': avg_monthly
        }])

        # 5. Run Engine
        results_df = apply_v0_rules(sim_df)
        result = results_df.iloc[0]

        st.divider()
        st.subheader("2. Credit Decision Engine")
        
        # Score Cards
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Behavior Score", f"{result['Score']:.0f} / 100")
        k2.metric("Risk Band", result['Band'])
        k3.metric("Failure Rate (60d)", f"{failure_rate*100:.1f}%")
        k4.metric("Est. Capacity", f"₦{median_vend:,.0f}")

        # Scenario Visualization
        scenarios = config.SCENARIOS.keys()
        viz_data = []
        for sc in scenarios:
            viz_data.append({
                "Scenario": sc,
                "Credit Limit": result[f"Amount_{sc}"],
                "Decision": result[f"Decision_{sc}"],
                "Reason": result[f"Reason_{sc}"]
            })
        viz_df = pd.DataFrame(viz_data)
        
        fig = px.bar(
            viz_df, x="Scenario", y="Credit Limit", color="Decision",
            text="Credit Limit", title=f"Approved Limits for {selected_user}",
            color_discrete_map={"APPROVED": "#00CC96", "REJECTED": "#EF553B"}
        )
        fig.update_traces(texttemplate='₦%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        # 6. Interactive Vend Simulation
        st.divider()
        st.subheader("3. Vend Simulation & Enforcement")
        st.info("Simulate the customer request flow to test 'Float Protection' and 'Repayment' logic.")

        # Inputs
        sc_col, bal_col, req_col = st.columns(3)
        with sc_col:
            active_scenario = st.selectbox("Active Risk Scenario", list(config.SCENARIOS.keys()), index=1)
        with bal_col:
            wallet_balance = st.number_input("Current Wallet Balance (₦)", value=0, step=100)
        with req_col:
            vend_request = st.number_input("Customer Request Amount (₦)", value=5000, step=500)

        # Logic
        limit = result[f"Amount_{active_scenario}"]
        decision = result[f"Decision_{active_scenario}"]
        reason = result[f"Reason_{active_scenario}"]

        # State Management for "Vend"
        if "vend_state" not in st.session_state:
            st.session_state.vend_state = "IDLE"

        # Check Eligibility
        if decision == "APPROVED":
            max_offer = min(limit, 20000) # Global cap if needed
            total_purchasing_power = wallet_balance + max_offer
            
            # Offer Card
            st.success(f"✅ Customer is Eligible! Approved Advance: **₦{max_offer:,.0f}**")
            
            with st.expander("View Offer Details", expanded=True):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Requested:** ₦{vend_request:,}")
                c1.markdown(f"**Wallet:** ₦{wallet_balance:,}")
                
                # Logic: Did they ask for more than they have?
                needed = max(0, vend_request - wallet_balance)
                
                if needed == 0:
                    st.warning("Customer has sufficient wallet balance. No credit needed.")
                elif needed > max_offer:
                    st.error(f"Insufficient Credit. Needs ₦{needed:,}, but limit is ₦{max_offer:,}.")
                else:
                    st.markdown(f"**Credit Required:** ₦{needed:,}")
                    st.markdown(f"**Repayment Due:** Next Vend")
                    
                    if st.button("✅ Accept & Dispense Token", key="vend_btn"):
                        st.session_state.vend_state = "COMPLETED"
                        st.session_state.last_vend = {
                            "meter": selected_user,
                            "amount": vend_request,
                            "credit_used": needed
                        }

        else:
            st.error(f"❌ Credit Declined ({active_scenario})")
            st.caption(f"Reason: {reason}")
            st.session_state.vend_state = "IDLE"

        # Success Message
        if st.session_state.vend_state == "COMPLETED" and st.session_state.last_vend['meter'] == selected_user:
            st.markdown("---")
            st.balloons()
            st.success(f"⚡ Token Generated for ₦{st.session_state.last_vend['amount']:,}")
            st.info(f"💰 **₦{st.session_state.last_vend['credit_used']:,}** recorded as debt. 100% recovery enforced on next transaction.")

        # Download Result
        st.markdown("---")
        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Analysis (CSV)", csv, f"decision_{selected_user}.csv", "text/csv")


# ==========================================
# MODE 2: MANUAL PROFILE BUILDER (Existing)
# ==========================================
elif app_mode == "Manual Profile Builder":
    st.subheader("Simulate a Customer Profile")
    st.info("Use sliders to test edge cases without needing raw data.")

    meter_id = st.text_input("Meter ID (Label)", value="TEST_USER_001")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📅 History")
        tenure_days = st.number_input("Total Tenure (Days)", min_value=0, value=90, step=10)
        vends_60d = st.slider("Vends in Last 60 Days", 0, 30, 5)
        recency_days = st.slider("Days Since Last Vend", 0, 90, 10)

    with col2:
        st.markdown("### 💰 Capacity")
        median_spend = st.number_input("Median Vend Amount (₦)", min_value=0, value=5000, step=500)
        total_vends = st.number_input("Total Lifetime Vends", min_value=1, value=15)
        avg_monthly = median_spend * (vends_60d / 2) if vends_60d > 0 else 0

    with col3:
        st.markdown("### ⚠️ Risk")
        failure_rate = st.slider("Failure Rate (%)", 0.0, 1.0, 0.1, step=0.05)
        volatility = st.slider("Volatility Score", 0.0, 2.0, 0.3)
        unique_devices = st.number_input("Unique Devices", min_value=1, max_value=10, value=1)

    input_data = {
        'Meter No': [meter_id],
        'tenure_days': [tenure_days],
        'vends_60d': [vends_60d],
        'recency_days': [recency_days],
        'median_vend_amount': [median_spend],
        'total_success_vends': [total_vends],
        'failure_rate': [failure_rate],
        'volatility': [volatility],
        'unique_devices': [unique_devices],
        'avg_monthly_spend': [avg_monthly]
    }
    
    if st.button("Analyze Profile", type="primary"):
        sim_df = pd.DataFrame(input_data)
        results_df = apply_v0_rules(sim_df)
        result = results_df.iloc[0]

        # Reuse visualization logic...
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Score", f"{result['Score']:.1f}")
        m2.metric("Band", result['Band'])
        st.dataframe(results_df)

# ==========================================
# MODE 3: BATCH PORTFOLIO ANALYSIS (Existing)
# ==========================================
elif app_mode == "Batch Portfolio Analysis":
    uploaded_file = st.sidebar.file_uploader("Upload Consolidated CSV", type=['csv'])

    if uploaded_file is not None:
        try:
            with st.spinner('Processing Portfolio...'):
                raw_df = load_and_clean_data(uploaded_file)
                features_df = calculate_features(raw_df)
                results_df = apply_v0_rules(features_df)
                
            st.success(f"Processed {len(results_df)} meters.")
            
            # Quick Stats
            st.subheader("Scenario Approvals")
            scenarios = config.SCENARIOS.keys()
            cols = st.columns(3)
            for i, sc in enumerate(scenarios):
                approved = results_df[results_df[f"Decision_{sc}"] == 'APPROVED']
                rate = (len(approved)/len(results_df))*100
                cols[i].metric(f"{sc}", f"{rate:.1f}%", f"{len(approved)} Users")

            st.dataframe(results_df)
            
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Full Report", csv, "monsera_results.csv", "text/csv")

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("👈 Upload 'consolidated_transactions.csv' for bulk analysis.")