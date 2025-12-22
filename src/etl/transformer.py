import pandas as pd
import numpy as np
from datetime import timedelta

def calculate_features(df, reference_date=None):
    """
    Aggregates transaction logs into meter-level behavioral features.
    Args:
        df (pd.DataFrame): Transaction data
        reference_date (datetime, optional): The 'Today' date for simulation. 
                                             Defaults to max date in data.
    """
    # Group by Meter No
    grouped_all = df.groupby('Meter No')
    
    # Filter for Successful transactions
    df_success = df[df['is_successful']].copy()
    grouped_success = df_success.groupby('Meter No')

    # --- KEY FIX: DYNAMIC REFERENCE DATE ---
    # If a date is provided (Time Travel), use it. Otherwise use the real max date.
    if reference_date:
        dataset_end_date = pd.to_datetime(reference_date)
    else:
        dataset_end_date = df['Entry Date'].max()
        
    date_60_days_ago = dataset_end_date - timedelta(days=60)
    
    # --- Helper Functions ---
    def get_recency(dates):
        if len(dates) == 0: return 999
        # Ensure we don't get negative days if reference_date is in the past
        days = (dataset_end_date - dates.max()).days
        return max(0, days)

    def get_vends_last_60d(group):
        if group.empty: return 0
        return group[group['Entry Date'] >= date_60_days_ago].shape[0]

    def get_avg_monthly_spend(group):
        if group.empty: return 0.0
        # Only calculate for the relevant window
        monthly_spend = group.set_index('Entry Date').resample('ME')['Amount'].sum()
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
    
    features['total_attempts'] = grouped_all.size()
    features['failure_rate'] = grouped_all.apply(get_failure_rate)
    
    success_metrics = pd.DataFrame()
    success_metrics['tenure_days'] = grouped_success['Entry Date'].apply(lambda x: (dataset_end_date - x.min()).days)
    success_metrics['recency_days'] = grouped_success['Entry Date'].apply(get_recency)
    success_metrics['vends_60d'] = grouped_success.apply(get_vends_last_60d)
    success_metrics['median_vend_amount'] = grouped_success['Amount'].median()
    success_metrics['avg_monthly_spend'] = grouped_success.apply(get_avg_monthly_spend)
    success_metrics['total_success_vends'] = grouped_success.size()
    success_metrics['volatility'] = grouped_success['Amount'].apply(get_volatility)
    success_metrics['unique_devices'] = grouped_success['User Agent'].apply(get_channel_stability)

    features = features.join(success_metrics)

    # Fill NaNs
    features['tenure_days'] = features['tenure_days'].fillna(0)
    features['recency_days'] = features['recency_days'].fillna(999)
    features['vends_60d'] = features['vends_60d'].fillna(0)
    features['median_vend_amount'] = features['median_vend_amount'].fillna(0)
    features['avg_monthly_spend'] = features['avg_monthly_spend'].fillna(0)
    features['total_success_vends'] = features['total_success_vends'].fillna(0)
    features['volatility'] = features['volatility'].fillna(1.0)
    features['unique_devices'] = features['unique_devices'].fillna(1)

    return features.reset_index().rename(columns={'index': 'Meter No'})