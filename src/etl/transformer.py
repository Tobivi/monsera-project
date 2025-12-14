# my-credit-project/src/etl/transformer.py
import pandas as pd
import numpy as np
from datetime import timedelta

def calculate_features(df):
    """
    Aggregates transaction logs into meter-level behavioral features.
    Updated to support V0 Behavioral Model.
    """
    print("Generating behavioral features...")

    # Group by Meter No
    grouped = df.groupby('Meter No')

    # Global dataset end date for "current time" calculations
    dataset_end_date = df['Entry Date'].max()
    date_60_days_ago = dataset_end_date - timedelta(days=60)
    
    # --- Helper Functions ---
    def get_tenure(dates):
        return (dataset_end_date - dates.min()).days

    def get_recency(dates):
        # Days since last vend (Step 1 Gate)
        return (dataset_end_date - dates.max()).days

    def get_vends_last_60d(group):
        # Count vends in the last 60 day window (Step 1 Gate)
        return group[group['Entry Date'] >= date_60_days_ago].shape[0]

    def get_avg_monthly_spend(group):
        monthly_spend = group.set_index('Entry Date').resample('M')['Amount'].sum()
        return monthly_spend.mean()

    def get_volatility(amounts):
        if len(amounts) < 2: return 1.0 
        mean = amounts.mean()
        if mean == 0: return 1.0
        return amounts.std() / mean

    def get_channel_stability(user_agents):
        # Count unique devices used (Step 1 Gate / Step 2 Reliability)
        return user_agents.nunique()

    # --- Aggregation ---
    features = pd.DataFrame()
    
    # Existing metrics
    features['tenure_days'] = grouped['Entry Date'].apply(get_tenure)
    features['avg_monthly_spend'] = grouped.apply(get_avg_monthly_spend)
    features['total_vends'] = grouped.size()
    features['volatility'] = grouped['Amount'].apply(get_volatility)
    
    # NEW metrics for V0 Model
    features['recency_days'] = grouped['Entry Date'].apply(get_recency)
    features['vends_60d'] = grouped.apply(get_vends_last_60d)
    features['median_vend_amount'] = grouped['Amount'].median() # Capacity Score
    features['unique_devices'] = grouped['User Agent'].apply(get_channel_stability)

    # Fill NaNs
    features = features.fillna(0)

    print(f"Features generated for {len(features)} unique meters.")
    return features