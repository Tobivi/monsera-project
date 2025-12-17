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
This dashboard simulates the **V0 Behavioral Model** across three risk scenarios.
Upload transaction logs to see how moving from 'Conservative' to 'Aggressive' impacts approval rates and credit limits.
""")

# --- SIDEBAR: CONFIG & UPLOAD ---
st.sidebar.header("1. Input Data")
uploaded_file = st.sidebar.file_uploader("Upload Transactions (CSV)", type=['csv'])

st.sidebar.markdown("---")
st.sidebar.header("Scenario Definitions")

def display_scenario_params(name, params):
    st.sidebar.subheader(f"{name}")
    st.sidebar.caption(f"Min Vends (60d): **{params['min_vends_60d']}**")
    st.sidebar.caption(f"Max Dormancy: **{params['max_dormancy_days']} days**")
    st.sidebar.caption(f"Limit Strategy: **{params['limit_strategy']}**")

for name, params in config.SCENARIOS.items():
    display_scenario_params(name, params)

# --- MAIN LOGIC ---
if uploaded_file is not None:
    try:
        with st.spinner('Running V0 Pipeline...'):
            # 1. Load Data
            # Streamlit uploads are file-like objects, which pd.read_csv accepts directly
            raw_df = load_and_clean_data(uploaded_file)
            
            # 2. Transform
            features_df = calculate_features(raw_df)
            
            # 3. Score
            results_df = apply_v0_rules(features_df)
            
        st.success(f"Successfully processed {len(results_df)} unique meters.")

        # --- METRICS CALCULATION ---
        scenarios = config.SCENARIOS.keys()
        metrics = []

        for sc in scenarios:
            decision_col = f"Decision_{sc}"
            amount_col = f"Amount_{sc}"
            
            approved = results_df[results_df[decision_col] == 'APPROVED']
            approval_rate = (len(approved) / len(results_df)) * 100
            avg_limit = approved[amount_col].mean() if not approved.empty else 0
            total_exposure = approved[amount_col].sum()
            
            metrics.append({
                "Scenario": sc,
                "Approval Rate": f"{approval_rate:.1f}%",
                "Avg Limit": f"₦{avg_limit:,.0f}",
                "Total Exposure": f"₦{total_exposure:,.0f}",
                "Count": len(approved)
            })

        # --- DASHBOARD ROW 1: KPI CARDS ---
        st.subheader("2. Scenario Comparison")
        cols = st.columns(3)
        
        for i, metric in enumerate(metrics):
            with cols[i]:
                st.metric(
                    label=f"{metric['Scenario']} Approval Rate",
                    value=metric['Approval Rate'],
                    delta=f"{metric['Count']} Users"
                )
                st.caption(f"Avg Limit: {metric['Avg Limit']}")
                st.caption(f"Total Exposure: {metric['Total Exposure']}")

        # --- DASHBOARD ROW 2: VISUALIZATION ---
        st.subheader("3. Impact Analysis")
        
        # Prepare data for plotting
        plot_data = []
        for sc in scenarios:
            amt_col = f"Amount_{sc}"
            temp = results_df[results_df[amt_col] > 0][amt_col]
            for val in temp:
                plot_data.append({'Scenario': sc, 'Credit Limit': val})
        
        plot_df = pd.DataFrame(plot_data)
        
        if not plot_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Credit Limit Distribution (Box Plot)**")
                fig = px.box(plot_df, x="Scenario", y="Credit Limit", color="Scenario", 
                             points="all", title="Spread of Approved Amounts")
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                st.markdown("**Approval Count by Band**")
                # Group by Band and Decision for the 'Moderate' Scenario as a representative
                viz_df = results_df.groupby(['Band', 'Decision_B_Moderate']).size().reset_index(name='Count')
                fig2 = px.bar(viz_df, x="Band", y="Count", color="Decision_B_Moderate", 
                              title="Risk Bands vs Decisions (Moderate Scenario)",
                              color_discrete_map={"APPROVED": "#00CC96", "REJECTED": "#EF553B"})
                st.plotly_chart(fig2, use_container_width=True)

        # --- DASHBOARD ROW 3: DETAILED DATA ---
        st.subheader("4. Customer Deep Dive")
        
        # Filter Options
        filter_scenario = st.selectbox("Select Scenario View:", list(scenarios), index=1)
        decision_col = f"Decision_{filter_scenario}"
        amount_col = f"Amount_{filter_scenario}"
        reason_col = f"Reason_{filter_scenario}"
        
        show_only_approved = st.checkbox("Show Only Approved", value=True)
        
        display_cols = ['Meter No', 'Score', 'Band', 'Median_Spend', 'Failure_Rate', decision_col, amount_col, reason_col]
        
        view_df = results_df[display_cols].copy()
        if show_only_approved:
            view_df = view_df[view_df[decision_col] == 'APPROVED']
            
        st.dataframe(view_df.style.format({
            'Score': "{:.1f}", 
            'Median_Spend': "₦{:.0f}",
            amount_col: "₦{:.0f}",
            'Failure_Rate': "{:.1%}"
        }), use_container_width=True)

        # --- DOWNLOAD ---
        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Full Analysis CSV",
            csv,
            "monsera_v0_scenario_analysis.csv",
            "text/csv",
            key='download-csv'
        )

    except Exception as e:
        st.error(f"An error occurred: {e}")
        # Print detailed error for debugging
        import traceback
        st.text(traceback.format_exc())

else:
    st.info("👈 Please upload your 'consolidated_transactions.csv' file in the sidebar to begin.")