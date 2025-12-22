import pandas as pd
import numpy as np
from datetime import timedelta

def calculate_features(df):
    """
    Aggregates transaction logs into meter-level behavioral features.
    Separates SUCCESSFUL transactions (for capacity) from ALL transactions (for friction risk).
    """
    print("Generating behavioral features...")

    # Group by Meter No
    grouped_all = df.groupby('Meter No')
    
    # Filter for Successful transactions for spend metrics
    df_success = df[df['is_successful']].copy()
    grouped_success = df_success.groupby('Meter No')

    # Global dataset end date
    dataset_end_date = df['Entry Date'].max()
    date_60_days_ago = dataset_end_date - timedelta(days=60)
    
    # --- Helper Functions ---
    def get_recency(dates):
        if len(dates) == 0: return 999
        return (dataset_end_date - dates.max()).days

    def get_vends_last_60d(group):
        if group.empty: return 0
        return group[group['Entry Date'] >= date_60_days_ago].shape[0]

    def get_avg_monthly_spend(group):
        if group.empty: return 0.0
        monthly_spend = group.set_index('Entry Date').resample('M')['Amount'].sum()
        return monthly_spend.mean()

    def get_volatility(amounts):
        if len(amounts) < 2: return 1.0 
        mean = amounts.mean()
        if mean == 0: return 1.0
        return amounts.std() / mean

    def get_channel_stability(user_agents):
        return user_agents.nunique()
    
    def get_failure_rate(group):
        total = len(group)
        if total == 0: return 0.0
        failures = total - group['is_successful'].sum()
        return failures / total

    # --- Aggregation ---
    features = pd.DataFrame(index=grouped_all.groups.keys())
    
    # A. RISK METRICS (Uses ALL transactions)
    features['total_attempts'] = grouped_all.size()
    features['failure_rate'] = grouped_all.apply(get_failure_rate)
    
    # B. SPEND METRICS (Uses SUCCESSFUL transactions only)
    # We map the success metrics to the main features dataframe
    
    # Calculate metrics on success group
    success_metrics = pd.DataFrame()
    success_metrics['tenure_days'] = grouped_success['Entry Date'].apply(lambda x: (dataset_end_date - x.min()).days)
    success_metrics['recency_days'] = grouped_success['Entry Date'].apply(get_recency)
    success_metrics['vends_60d'] = grouped_success.apply(get_vends_last_60d)
    success_metrics['median_vend_amount'] = grouped_success['Amount'].median()
    success_metrics['avg_monthly_spend'] = grouped_success.apply(get_avg_monthly_spend)
    success_metrics['total_success_vends'] = grouped_success.size()
    success_metrics['volatility'] = grouped_success['Amount'].apply(get_volatility)
    success_metrics['unique_devices'] = grouped_success['User Agent'].apply(get_channel_stability)

    # Merge success metrics into features (left join to keep failed-only users)
    features = features.join(success_metrics)

    # Fill NaNs for users who have 0 successful transactions
    features['tenure_days'] = features['tenure_days'].fillna(0)
    features['recency_days'] = features['recency_days'].fillna(999) # Very old
    features['vends_60d'] = features['vends_60d'].fillna(0)
    features['median_vend_amount'] = features['median_vend_amount'].fillna(0)
    features['avg_monthly_spend'] = features['avg_monthly_spend'].fillna(0)
    features['total_success_vends'] = features['total_success_vends'].fillna(0)
    features['volatility'] = features['volatility'].fillna(1.0) # High risk default
    features['unique_devices'] = features['unique_devices'].fillna(1)

    print(f"Features generated for {len(features)} unique meters.")
    return features.reset_index().rename(columns={'index': 'Meter No'})