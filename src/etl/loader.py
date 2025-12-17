import pandas as pd
import numpy as np

def load_and_clean_data(filepath):
    """
    Loads consolidated transaction data.
    IMPORTANT: Retains FAILED transactions to calculate failure rates.
    """
    print(f"Loading data from {filepath}...")
    
    df = pd.read_csv(filepath)

    # 1. Standardize Column Names
    column_mapping = {
        'User_ID': 'Meter No',
        'Transaction_Date': 'Entry Date',
        'Access_Source': 'User Agent',
        'Status': 'Status'
    }
    df = df.rename(columns=column_mapping)

    # 2. Mark Success/Failure (Do not drop rows yet)
    # We need failures to calculate "Friction Risk"
    valid_statuses = ['SUCCESS', 'SUCCESSFUL', 'COMPLETED']
    
    # Handle case sensitivity and whitespace
    if 'Status' in df.columns:
        df['is_successful'] = df['Status'].astype(str).str.upper().str.strip().isin(valid_statuses)
    else:
        # If no status column, assume all are valid (fallback)
        df['is_successful'] = True

    # 3. Parse Dates
    df['Entry Date'] = pd.to_datetime(df['Entry Date'], errors='coerce')
    df = df.dropna(subset=['Entry Date'])

    # 4. Clean Amounts
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

    # 5. Clean ID
    df['Meter No'] = df['Meter No'].astype(str).str.strip()

    # Sort by date
    df = df.sort_values(by='Entry Date')

    print(f"Data loaded successfully: {len(df)} total transactions (Success + Failure).")
    return df