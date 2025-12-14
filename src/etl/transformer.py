# feature_engineering.py
import pandas as pd
import numpy as np

def calculate_features(df):
    """
    Aggregates transaction logs into meter-level behavioral features.
    Reference PRD: Data Ingestion and Feature Extraction [cite: 35]
    """
    print("Generating behavioral features...")

    # Group by Meter No
    grouped = df.groupby('Meter No')

    # 1. Tenure (Days since first vend) [cite: 36]
    # We use the max date in the dataset as the 'current' date for calculation
    dataset_end_date = df['Entry Date'].max()
    
    def get_tenure(dates):
        first_vend = dates.min()
        return (dataset_end_date - first_vend).days

    # 2. Average Monthly Spend [cite: 36]
    # We group by Month-Year to get monthly totals, then average them
    def get_avg_monthly_spend(group):
        # Resample to monthly frequency based on Entry Date
        monthly_spend = group.set_index('Entry Date').resample('M')['Amount'].sum()
        return monthly_spend.mean()

    # 3. Volatility (Coefficient of Variation) [cite: 36]
    # Std Dev / Mean. Higher means erratic income/spending.
    def get_volatility(amounts):
        if len(amounts) < 2: 
            return 1.0 # High risk if not enough data
        mean = amounts.mean()
        std = amounts.std()
        if mean == 0: return 1.0
        return std / mean

    # Aggregation
    features = pd.DataFrame()
    features['tenure_days'] = grouped['Entry Date'].apply(get_tenure)
    features['avg_monthly_spend'] = grouped.apply(get_avg_monthly_spend)
    features['total_vends'] = grouped.size() # Frequency [cite: 36]
    features['volatility'] = grouped['Amount'].apply(get_volatility)
    
    # Fill any NaNs (e.g., volatility for single transactions)
    features = features.fillna(0)

    print(f"Features generated for {len(features)} unique meters.")
    return features