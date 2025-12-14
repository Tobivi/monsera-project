# src/credit_engine/scoring.py
import pandas as pd
import numpy as np
# CHANGE THIS LINE: Use the full path to import config
from src.credit_engine import config 

def apply_enhanced_v0_logic(features_df):
    """
    Implements the 3-Step V0 Behavioral Model:
    1. Hard Gates (Eligibility)
    2. Behavior Score (0-100)
    3. Credit Limit Calculation (Base Limit + Caps)
    """
    print("Running Enhanced V0 Model...")
    results = []

    for meter_id, row in features_df.iterrows():
        # --- 1. HARD GATES ---
        rejection_reasons = []
        is_eligible = True

        # Gate: Insufficient History (< 6 vends in last 60 days)
        if row['vends_60d'] < config.GATE_MIN_VENDS_60_DAYS:
            is_eligible = False
            rejection_reasons.append(f"Insufficient history ({row['vends_60d']} vends/60d)")

        # Gate: Dormant Behavior (Last vend > 30 days ago)
        if row['recency_days'] > config.GATE_MAX_DAYS_DORMANT:
            is_eligible = False
            rejection_reasons.append(f"Dormant (Last vend {row['recency_days']} days ago)")

        # --- 2. BEHAVIOR SCORE (0-100) ---
        # Only calculate score if eligible (or useful for analysis)
        score = 0
        band = 'D'
        
        # A. Frequency Score (0-30)
        # Simple interpolation: 10 vends/month = 30 points
        avg_vends_per_month = row['total_vends'] / max(1, (row['tenure_days']/30))
        freq_score = min(config.WEIGHT_FREQUENCY, (avg_vends_per_month / config.REF_HIGH_FREQ_MONTHLY) * config.WEIGHT_FREQUENCY)
        
        # B. Consistency Score (0-25)
        # Inverse of volatility. Lower volatility = Higher score.
        # If vol > 1.0, score is 0. If vol = 0, score is max.
        cons_score = max(0, config.WEIGHT_CONSISTENCY * (1 - row['volatility']))
        
        # C. Capacity Score (0-25)
        # Uses Median Vend Amount. Assuming Median > 3000 is "Good" (Example Logic)
        # Scaled against a reference of 5000 (Adjust based on data reality)
        cap_score = min(config.WEIGHT_CAPACITY, (row['median_vend_amount'] / 5000) * config.WEIGHT_CAPACITY)

        # D. Reliability Score (0-20)
        # Penalize for multiple devices (proxy for channel stability)
        # 1 device = Full points, 3+ devices = 0 points
        rel_score = max(0, config.WEIGHT_RELIABILITY - (row['unique_devices'] - 1) * 10)

        total_score = freq_score + cons_score + cap_score + rel_score
        
        # Determine Band
        if total_score >= config.SCORE_BANDS['A']['min_score']: band = 'A'
        elif total_score >= config.SCORE_BANDS['B']['min_score']: band = 'B'
        elif total_score >= config.SCORE_BANDS['C']['min_score']: band = 'C'
        else: band = 'D'

        # --- 3. CREDIT LIMIT CALCULATION ---
        final_limit = 0.0
        
        if is_eligible and band != 'D':
            band_config = config.SCORE_BANDS[band]
            
            # Base Limit = min( CapByBand, k * MedianVendAmount )
            base_limit = min(band_config['cap'], band_config['k'] * row['median_vend_amount'])
            
            # Apply Global Min/Max Constraints (User Requirement)
            # Only approve if calculated limit >= Global Min
            if base_limit >= config.MIN_LOAN_AMOUNT:
                final_limit = min(base_limit, config.MAX_LOAN_AMOUNT)
                decision = "APPROVED"
                reason = "Eligible"
            else:
                decision = "REJECTED"
                final_limit = 0.0
                rejection_reasons.append(f"Calculated limit ({base_limit}) below min threshold")
                reason = "; ".join(rejection_reasons)
        else:
            decision = "REJECTED"
            reason = "; ".join(rejection_reasons) if rejection_reasons else f"Low Score (Band {band})"

        results.append({
            'Meter No': meter_id,
            'Score': round(total_score, 1),
            'Band': band,
            'Recency (Days)': row['recency_days'],
            'Vends (60d)': row['vends_60d'],
            'Median Spend': row['median_vend_amount'],
            'Decision': decision,
            'Approved Amount': round(final_limit, 2),
            'Reason': reason
        })

    return pd.DataFrame(results)

def apply_v0_rules(features_df):
    return apply_enhanced_v0_logic(features_df)