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
st.set_page_config(page_title="Monsera V0 Credit Demo", layout="wide")

st.title("⚡ Monsera V0 Credit Engine")
st.markdown("""
**Hybrid Demo Mode:** Simulate a single user manually OR upload a batch file to test the portfolio.
""")

# --- SIDEBAR: MODE SELECTION ---
st.sidebar.header("Configuration")
app_mode = st.sidebar.radio("Select Mode:", ["Single User Simulation", "Batch Upload (CSV)"])

st.sidebar.markdown("---")
st.sidebar.header("Scenario Rules")

def display_scenario_params(name, params):
    st.sidebar.subheader(f"{name}")
    st.sidebar.caption(f"Min Vends: **{params['min_vends_60d']}**")
    st.sidebar.caption(f"Max Dormancy: **{params['max_dormancy_days']} days**")
    st.sidebar.caption(f"Limit Strategy: **{params['limit_strategy']}**")

for name, params in config.SCENARIOS.items():
    display_scenario_params(name, params)

# ==========================================
# MODE 1: SINGLE USER SIMULATION
# ==========================================
if app_mode == "Single User Simulation":
    st.subheader("1. Simulation Inputs")
    st.info("Adjust the sliders below to simulate a customer profile and see real-time decisions.")

    # Create 3 columns for inputs
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📅 History & Activity")
        tenure_days = st.number_input("Total Tenure (Days)", min_value=0, value=90, step=10, help="Days since first transaction")
        vends_60d = st.slider("Vends in Last 60 Days", 0, 30, 5, help="Key eligibility metric")
        recency_days = st.slider("Days Since Last Vend", 0, 90, 10, help="Dormancy check")

    with col2:
        st.markdown("### 💰 Financial Capacity")
        median_spend = st.number_input("Median Vend Amount (₦)", min_value=0, value=5000, step=500)
        total_vends = st.number_input("Total Lifetime Vends", min_value=1, value=15)
        # Derived metric for scoring
        avg_monthly = median_spend * (vends_60d / 2) if vends_60d > 0 else 0

    with col3:
        st.markdown("### ⚠️ Risk & Stability")
        failure_rate = st.slider("Failure Rate (%)", 0.0, 1.0, 0.1, step=0.05)
        volatility = st.slider("Volatility Score", 0.0, 2.0, 0.3, help="0.0 = Consistent, 1.0+ = Erratic")
        unique_devices = st.number_input("Unique Devices Used", min_value=1, max_value=10, value=1)

    # Build DataFrame for the Engine
    input_data = {
        'Meter No': ['SIMULATED_USER_001'],
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
    
    sim_df = pd.DataFrame(input_data)

    if st.button("Run Simulation", type="primary"):
        # Run Scoring
        result = apply_v0_rules(sim_df).iloc[0]

        st.divider()
        st.subheader("2. Decision Dashboard")
        
        # --- Top Level Metrics ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Behavior Score", f"{result['Score']:.1f} / 100")
        m2.metric("Risk Band", result['Band'])
        m3.metric("Median Capacity", f"₦{median_spend:,.0f}")

        # --- PREPARE DATA FOR VISUALIZATION ---
        scenarios = config.SCENARIOS.keys()
        viz_data = []
        
        for sc in scenarios:
            decision = result[f"Decision_{sc}"]
            amount = result[f"Amount_{sc}"]
            reason = result[f"Reason_{sc}"]
            
            viz_data.append({
                "Scenario": sc,
                "Credit Limit": amount,
                "Decision": decision,
                "Reason": reason
            })

        viz_df = pd.DataFrame(viz_data)

        # --- VISUALIZATION: Limit Comparison ---
        st.subheader("3. Scenario Impact Analysis")
        
        c1, c2 = st.columns([2, 1])
        
        with c1:
            # Bar Chart: Limit by Scenario
            fig = px.bar(
                viz_df, 
                x="Scenario", 
                y="Credit Limit", 
                color="Decision",
                text="Credit Limit",
                title="Approved Credit Limit by Scenario",
                color_discrete_map={"APPROVED": "#00CC96", "REJECTED": "#EF553B"},
                labels={"Credit Limit": "Limit (₦)"}
            )
            fig.update_traces(texttemplate='₦%{text:,.0f}', textposition='outside')
            fig.update_layout(yaxis_range=[0, max(20000, viz_df['Credit Limit'].max() * 1.2)]) # Add headroom
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            # Detailed Cards for each Scenario
            st.markdown("**Scenario Breakdown**")
            for index, row in viz_df.iterrows():
                with st.expander(f"{row['Scenario']}", expanded=True):
                    if row['Decision'] == "APPROVED":
                        st.success(f"✅ **APPROVED: ₦{row['Credit Limit']:,.0f}**")
                    else:
                        st.error(f"❌ **REJECTED**")
                        st.caption(f"Reason: {row['Reason']}")


# ==========================================
# MODE 2: BATCH UPLOAD (Existing Logic)
# ==========================================
elif app_mode == "Batch Upload (CSV)":
    uploaded_file = st.sidebar.file_uploader("Upload Transactions (CSV)", type=['csv'])

    if uploaded_file is not None:
        try:
            with st.spinner('Running V0 Pipeline...'):
                raw_df = load_and_clean_data(uploaded_file)
                features_df = calculate_features(raw_df)
                results_df = apply_v0_rules(features_df)
                
            st.success(f"Successfully processed {len(results_df)} unique meters.")

            # --- METRICS & DASHBOARD ---
            scenarios = config.SCENARIOS.keys()
            metrics = []

            for sc in scenarios:
                decision_col = f"Decision_{sc}"
                amount_col = f"Amount_{sc}"
                
                approved = results_df[results_df[decision_col] == 'APPROVED']
                approval_rate = (len(approved) / len(results_df)) * 100 if len(results_df) > 0 else 0
                avg_limit = approved[amount_col].mean() if not approved.empty else 0
                total_exposure = approved[amount_col].sum()
                
                metrics.append({
                    "Scenario": sc,
                    "Approval Rate": f"{approval_rate:.1f}%",
                    "Avg Limit": f"₦{avg_limit:,.0f}",
                    "Total Exposure": f"₦{total_exposure:,.0f}",
                    "Count": len(approved)
                })

            st.subheader("2. Scenario Comparison")
            cols = st.columns(3)
            for i, metric in enumerate(metrics):
                with cols[i]:
                    st.metric(label=f"{metric['Scenario']} Rate", value=metric['Approval Rate'], delta=f"{metric['Count']} Users")
                    st.caption(f"Avg Limit: {metric['Avg Limit']}")
                    st.caption(f"Total Exposure: {metric['Total Exposure']}")

            st.subheader("3. Impact Analysis")
            
            # Box Plot for Limits
            plot_data = []
            for sc in scenarios:
                amt_col = f"Amount_{sc}"
                temp = results_df[results_df[amt_col] > 0][amt_col]
                for val in temp:
                    plot_data.append({'Scenario': sc, 'Credit Limit': val})
            
            if plot_data:
                plot_df = pd.DataFrame(plot_data)
                fig = px.box(plot_df, x="Scenario", y="Credit Limit", color="Scenario", points="all", title="Portfolio Limit Distribution")
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("4. Detailed Data")
            st.dataframe(results_df)

            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results", csv, "monsera_results.csv", "text/csv")

        except Exception as e:
            st.error(f"An error occurred: {e}")
            import traceback
            st.text(traceback.format_exc())
    else:
        st.info("👈 Please upload 'consolidated_transactions.csv' to begin batch analysis.")