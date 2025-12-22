import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

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

# --- HEADER ---
st.title("⚡ Monsera V0 Credit Engine")
st.markdown("""
**Behavioral Eligibility & Advance-Sizing Model**
""")

# --- SIDEBAR: GLOBAL CONFIG ---
st.sidebar.header("System Configuration")
app_mode = st.sidebar.radio("Select Interface:", ["Interactive Simulation", "Batch Portfolio Upload"])

st.sidebar.markdown("---")
st.sidebar.header("Active Scenarios")

def display_scenario_params(name, params):
    st.sidebar.subheader(f"{name}")
    st.sidebar.caption(f"Min Vends: **{params['min_vends_60d']}**")
    st.sidebar.caption(f"Limit Strategy: **{params['limit_strategy']}**")

for name, params in config.SCENARIOS.items():
    display_scenario_params(name, params)

# ==========================================
# MODE 1: INTERACTIVE SIMULATION
# ==========================================
if app_mode == "Interactive Simulation":
    
    # We use Tabs to separate the "Sales Demo" from the "Technical Sandbox"
    tab_demo, tab_analyst = st.tabs(["🚀 Stakeholder Demo (Live)", "📊 Analyst Sandbox (Technical)"])

    # ---------------------------------------------------------
    # TAB 1: STAKEHOLDER DEMO (The "Real World" Scenario)
    # ---------------------------------------------------------
    with tab_demo:
        st.subheader("Live Transaction Simulation")
        st.caption("Simulate the customer experience at the point of sale (POS).")

        # --- 1. CONTEXT INPUTS ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("### 1. Customer Profile")
            # DisCo Selection (Metadata for the demo receipt)
            disco = st.selectbox("Distribution Company (DisCo)", 
                               ["Ikeja Electric", "Eko Electricity", "Abuja Electric", "Enugu Electric", "Port Harcourt Electric"])
            
            # Persona Selection (Shortcuts for complex slider configs)
            persona = st.selectbox("Customer Persona", 
                                 ["🌟 Prime User (High Trust)", 
                                  "👶 New Starter (Limited History)", 
                                  "⚠️ High Risk (Erratic Payment)",
                                  "💤 Dormant User (Returning)"])

        with c2:
            st.markdown("### 2. Wallet Context")
            wallet_balance = st.number_input("Current Wallet Balance (₦)", value=500, step=100, help="Money the user currently has.")
            
        with c3:
            st.markdown("### 3. User Request")
            vend_request = st.number_input("Electricity Requested (₦)", value=5000, step=500, help="Amount the user WANTS to buy.")

        st.divider()

        # --- 2. RUN SIMULATION BUTTON ---
        if st.button("⚡ Attempt Vend", type="primary", use_container_width=True):
            
            # --- MAP PERSONA TO DATA (Hidden Logic) ---
            # This accounts for "real scenarios" where you want to show distinct behaviors without manual input
            if "Prime User" in persona:
                sim_data = {'Meter No': ['DEMO_PRIME'], 'tenure_days': [365], 'vends_60d': [12], 'recency_days': [5], 
                            'median_vend_amount': [10000], 'total_success_vends': [50], 'failure_rate': [0.0], 'volatility': [0.1], 'unique_devices': [1], 'avg_monthly_spend': [20000]}
            elif "New Starter" in persona:
                sim_data = {'Meter No': ['DEMO_NEW'], 'tenure_days': [40], 'vends_60d': [4], 'recency_days': [10], 
                            'median_vend_amount': [2000], 'total_success_vends': [4], 'failure_rate': [0.0], 'volatility': [0.8], 'unique_devices': [1], 'avg_monthly_spend': [4000]}
            elif "High Risk" in persona:
                sim_data = {'Meter No': ['DEMO_RISK'], 'tenure_days': [100], 'vends_60d': [8], 'recency_days': [2], 
                            'median_vend_amount': [3000], 'total_success_vends': [20], 'failure_rate': [0.6], 'volatility': [1.5], 'unique_devices': [4], 'avg_monthly_spend': [12000]}
            elif "Dormant" in persona:
                sim_data = {'Meter No': ['DEMO_DORMANT'], 'tenure_days': [300], 'vends_60d': [2], 'recency_days': [50], 
                            'median_vend_amount': [5000], 'total_success_vends': [15], 'failure_rate': [0.1], 'volatility': [0.3], 'unique_devices': [1], 'avg_monthly_spend': [5000]}
            
            # Run Engine
            results_df = apply_v0_rules(pd.DataFrame(sim_data))
            result = results_df.iloc[0]
            
            # Use "Balanced Growth" scenario as the default for the Demo
            approved_limit = result['Amount_2_Balanced_Growth']
            decision = result['Decision_2_Balanced_Growth']
            reason = result['Reason_2_Balanced_Growth']
            
            # --- 3. DECISION LOGIC (THE STORY) ---
            total_purchasing_power = wallet_balance + approved_limit
            
            # Scenario A: User has enough cash, no credit needed (Pass-through)
            if wallet_balance >= vend_request:
                st.success(f"✅ **Vend Successful** (Paid via Wallet)")
                st.info("User had sufficient balance. No credit accessed.")
                
            # Scenario B: Credit Approved & Sufficient
            elif decision == "APPROVED" and total_purchasing_power >= vend_request:
                credit_needed = vend_request - wallet_balance
                
                # The "Hero" Card
                st.success(f"✅ **Vend Approved via Monsera Credit**")
                
                # Financial Breakdown
                k1, k2, k3 = st.columns(3)
                k1.metric("Wallet Deducted", f"₦{wallet_balance:,}")
                k2.metric("Credit Advanced", f"₦{credit_needed:,.0f}", delta="Monsera Covered This")
                k3.metric("Units Vended", f"₦{vend_request:,}", help="Total Token Value")
                
                # Repayment Preview (Critical for DisCo Trust)
                st.warning(
                    f"📅 **Repayment Schedule:**\n"
                    f"The **₦{credit_needed:,.0f}** advance will be automatically recovered "
                    f"from the customer's next successful vend on **{disco}**."
                )

            # Scenario C: Credit Approved but Limit Too Low
            elif decision == "APPROVED":
                st.warning(f"⚠️ **Partial Eligibility Only**")
                st.write(f"User requested **₦{vend_request:,}**, but total purchasing power is only **₦{total_purchasing_power:,.0f}**.")
                
                col_a, col_b = st.columns(2)
                col_a.metric("Wallet", f"₦{wallet_balance:,}")
                col_a.metric("Max Credit Limit", f"₦{approved_limit:,.0f}")
                col_b.info("Suggestion: Offer user the maximum available amount.")

            # Scenario D: Declined
            else:
                st.error(f"❌ **Credit Declined**")
                st.write(f"**Reason:** {reason}")
                st.caption(f"DisCo: {disco} | Risk Band: {result['Band']}")


    # ---------------------------------------------------------
    # TAB 2: ANALYST SANDBOX (Original Technical View)
    # ---------------------------------------------------------
    with tab_analyst:
        st.subheader("Parameter Sensitivity Analysis")
        st.info("Fine-tune individual parameters to test edge cases.")

        meter_id = st.text_input("Meter ID", value="TEST_USER_001")
        
        # Sliders
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### Activity")
            tenure_days = st.number_input("Tenure (Days)", 90)
            vends_60d = st.slider("Vends (60d)", 0, 30, 5)
            recency_days = st.slider("Days Since Last", 0, 90, 10)

        with col2:
            st.markdown("### Capacity")
            median_spend = st.number_input("Median Vend (₦)", 5000)
            total_vends = st.number_input("Total Vends", 15)
            avg_monthly = median_spend * (vends_60d / 2) if vends_60d > 0 else 0

        with col3:
            st.markdown("### Risk")
            failure_rate = st.slider("Fail Rate", 0.0, 1.0, 0.1)
            volatility = st.slider("Volatility", 0.0, 2.0, 0.3)
            unique_devices = st.number_input("Devices", 1)

        # Build DF
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
        
        if st.button("Run Analyst Simulation", type="secondary"):
            results_df = apply_v0_rules(pd.DataFrame(input_data))
            result = results_df.iloc[0]

            # Display raw metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Score", f"{result['Score']:.1f}")
            m2.metric("Band", result['Band'])
            m3.metric("Limit (Balanced)", f"₦{result['Amount_2_Balanced_Growth']:,.0f}")
            
            st.dataframe(results_df)


# ==========================================
# MODE 2: BATCH PORTFOLIO UPLOAD
# ==========================================
elif app_mode == "Batch Portfolio Upload":
    st.header("📂 Bulk Portfolio Analysis")
    st.markdown("Upload `consolidated_transactions.csv` to score thousands of users at once.")

    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv'])

    if uploaded_file is not None:
        try:
            with st.spinner('Processing Portfolio...'):
                # 1. LOAD & CLEAN
                raw_df = load_and_clean_data(uploaded_file)
                
                # FIX: Ensure User_ID maps to Meter No if needed
                if "User_ID" in raw_df.columns:
                    raw_df = raw_df.rename(columns={"User_ID": "Meter No"})
                
                # 2. TRANSFORM
                features_df = calculate_features(raw_df)
                
                # 3. SCORE
                results_df = apply_v0_rules(features_df)
                
            st.success(f"Processed {len(results_df)} meters successfully.")

            # --- DisCo Breakdown (Requested Feature) ---
            if "Service_Provider" in raw_df.columns:
                st.subheader("Analysis by DisCo")
                # Merge decision back with provider info for analysis
                # (This is a simplified approach, taking the first provider seen for each meter)
                provider_map = raw_df[['Meter No', 'Service_Provider']].drop_duplicates('Meter No')
                merged = results_df.merge(provider_map, on='Meter No', how='left')
                
                # Show approval rate by DisCo
                disco_stats = merged.groupby('Service_Provider').apply(
                    lambda x: pd.Series({
                        'Total Users': len(x),
                        'Approved': len(x[x['Decision_2_Balanced_Growth'] == 'APPROVED']),
                        'Approval Rate': f"{(len(x[x['Decision_2_Balanced_Growth'] == 'APPROVED']) / len(x) * 100):.1f}%",
                        'Avg Limit': x[x['Decision_2_Balanced_Growth'] == 'APPROVED']['Amount_2_Balanced_Growth'].mean()
                    })
                )
                st.dataframe(disco_stats)

            # --- STANDARD METRICS ---
            st.subheader("Scenario Comparison")
            
            scenarios = config.SCENARIOS.keys()
            metrics = []
            for sc in scenarios:
                approved = results_df[results_df[f"Decision_{sc}"] == 'APPROVED']
                metrics.append({
                    "Scenario": sc,
                    "Users Approved": len(approved),
                    "Exposure": f"₦{approved[f'Amount_{sc}'].sum():,.0f}"
                })
            
            st.dataframe(pd.DataFrame(metrics))

            # Download
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Scored Portfolio", csv, "monsera_scored.csv", "text/csv")

        except Exception as e:
            st.error(f"Error: {e}")