import pandas as pd
import numpy as np
from src.credit_engine import config

def calculate_score(row):
    """Calculates the 0-100 Behavior Score"""
    # A. Frequency Score (0-30)
    avg_vends_per_month = row['total_success_vends'] / max(1, (row['tenure_days']/30))
    freq_score = min(config.WEIGHT_FREQUENCY, (avg_vends_per_month / config.REF_HIGH_FREQ_MONTHLY) * config.WEIGHT_FREQUENCY)
    
    # B. Consistency Score (0-25)
    cons_score = max(0, config.WEIGHT_CONSISTENCY * (1 - row['volatility']))
    
    # C. Capacity Score (0-25) - Relative to 5000 baseline
    cap_score = min(config.WEIGHT_CAPACITY, (row['median_vend_amount'] / 5000) * config.WEIGHT_CAPACITY)

    # D. Reliability Score (0-20)
    rel_score = max(0, config.WEIGHT_RELIABILITY - (row['unique_devices'] - 1) * 10)

    total = freq_score + cons_score + cap_score + rel_score
    
    # Determine Band
    if total >= config.SCORE_BANDS['A']: band = 'A'
    elif total >= config.SCORE_BANDS['B']: band = 'B'
    elif total >= config.SCORE_BANDS['C']: band = 'C'
    else: band = 'D'
    
    return round(total, 1), band

def apply_scenario(row, score, band, scenario_name, params):
    """
    Applies Gates and calculates Limit with Score-Based Interpolation.
    """
    reasons = []
    is_eligible = True
    
    # --- 1. HARD GATES ---
    if row['vends_60d'] < params['min_vends_60d']:
        is_eligible = False
        reasons.append(f"Not enough history (< {params['min_vends_60d']})")
        
    if row['recency_days'] > params['max_dormancy_days']:
        is_eligible = False
        reasons.append(f"Too dormant (> {params['max_dormancy_days']} days)")
        
    if row['failure_rate'] > params['max_failure_rate']:
        is_eligible = False
        reasons.append(f"Failure rate too high (> {round(params['max_failure_rate']*100)}%)")

    # --- 2. LIMIT CALCULATION ---
    amount = 0.0
    multiplier = params['multipliers'].get(band, 0.0)
    
    if is_eligible and multiplier > 0:
        
        # --- NEW: SCORE FINE-TUNING ---
        # We adjust the multiplier based on how high the score is within the band.
        # This creates a continuous distribution of limits (143+ variants) instead of just 7 buckets.
        # Logic: For every point above the band floor, add 0.5% to the limit.
        
        band_floor = config.SCORE_BANDS.get(band, 0)
        score_surplus = max(0, score - band_floor)
        
        # Fine-tune factor: 1.0 (base) + extra boost
        fine_tune_factor = 1 + (score_surplus * 0.005) # 0.5% boost per point
        
        # Continuous Sizing
        raw_limit = row['median_vend_amount'] * multiplier * fine_tune_factor
        
        # --- SOFT PENALTIES ---
        soft_dormancy = params.get('soft_dormancy_threshold', 30)
        if row['recency_days'] > soft_dormancy:
            raw_limit *= 0.6  
            reasons.append(f"Dormancy Penalty (> {soft_dormancy}d)")
            
        soft_failure = params.get('soft_failure_threshold', 0.2)
        if row['failure_rate'] > soft_failure:
            raw_limit *= 0.7  
            reasons.append(f"Friction Penalty (> {round(soft_failure*100)}%)")

        # Cap at Global Max (or specific scenario cap if implemented)
        raw_limit = min(raw_limit, config.GLOBAL_MAX_LOAN)

        # --- UPDATED: ROUNDING TO NEAREST 1000 ---
        # This forces clean numbers like 3000, 4000, 5000...
        # Changed from 500 to 1000 steps as requested.
        if raw_limit >= config.GLOBAL_MIN_LOAN:
             amount = 1000 * round(raw_limit / 1000)
        else:
            amount = 0.0
            reasons.append("Below Min Loan Size")
            
    decision = "APPROVED" if amount > 0 else "REJECTED"
    reason_text = "; ".join(reasons) if reasons else "Clean Approval"
    
    return {
        f"Decision_{scenario_name}": decision,
        f"Amount_{scenario_name}": round(amount, 0),
        f"Reason_{scenario_name}": reason_text
    }

def apply_v0_rules(features_df):
    print("Running Multi-Scenario V0 Simulation...")
    results = []

    for meter_id, row in features_df.iterrows():
        # Calculate Base Score (Invariant across scenarios)
        score, band = calculate_score(row)
        
        row_result = {
            'Meter No': meter_id,
            'Score': score,
            'Band': band,
            'Recency': row['recency_days'],
            'Vends_60d': row['vends_60d'],
            'Failure_Rate': round(row['failure_rate'], 2),
            'Median_Spend': row['median_vend_amount']
        }
        
        # Run all Scenarios
        for name, params in config.SCENARIOS.items():
            scenario_result = apply_scenario(row, score, band, name, params)
            row_result.update(scenario_result)
            
        results.append(row_result)

    return pd.DataFrame(results)