# data_loader.py
import pandas as pd
import numpy as np

def load_and_clean_data(filepath):
    """
    Loads raw vending data and performs basic cleaning.
    """
    print(f"Loading data from {filepath}...")
    
    # Load CSV
    # Note: 'Meter No' is often read as float (scientific notation) by default, 
    # so we force it to string or object if possible, but cleaning is usually needed after.
    df = pd.read_csv(filepath)

    # 1. Parse Dates [cite: 35]
    # 'Entry Date' seems to be the transaction time
    df['Entry Date'] = pd.to_datetime(df['Entry Date'], errors='coerce')
    
    # Drop rows with invalid dates
    df = df.dropna(subset=['Entry Date'])

    # 2. Clean Amounts [cite: 36]
    # Ensure Amount is numeric
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

    # 3. Clean Meter Numbers
    # The CSV shows Meter No as '1.9521E+11'. We need to standardize this.
    def clean_meter_id(x):
        try:
            # Convert scientific notation float to full integer string
            return str(int(float(x)))
        except (ValueError, TypeError):
            return str(x)

    df['Meter No'] = df['Meter No'].apply(clean_meter_id)

    # Sort by date for accurate timeline calculations
    df = df.sort_values(by='Entry Date')

    print(f"Data loaded successfully: {len(df)} transactions found.")
    return df