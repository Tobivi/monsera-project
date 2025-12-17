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
    Applies specific Gates and Limit Logic for a single scenario.
    """
    reasons = []
    is_eligible = True
    
    # 1. Gates
    if row['vends_60d'] < params['min_vends_60d']:
        is_eligible = False
        reasons.append(f"< {params['min_vends_60d']} vends")
        
    if row['recency_days'] > params['max_dormancy_days']:
        is_eligible = False
        reasons.append(f"> {params['max_dormancy_days']} days dormant")
        
    if row['failure_rate'] > params['max_failure_rate']:
        is_eligible = False
        reasons.append(f"High Failure Rate ({round(row['failure_rate']*100)}%)")

    # 2. Limit Calculation
    amount = 0.0
    
    if is_eligible and band != 'D':
        multiplier = params['multipliers'][band]
        
        # Continuous Sizing: Limit = Median * Multiplier
        raw_limit = row['median_vend_amount'] * multiplier
        
        # If Tiered (Conservative), clamp it to the Band Cap
        if params['limit_strategy'] == 'Tiered':
            band_cap = params['tier_caps'][band]
            raw_limit = min(raw_limit, band_cap)
            
        # Global Constraints
        if raw_limit < config.GLOBAL_MIN_LOAN:
            amount = 0.0
            reasons.append("Below Min Loan Size")
        else:
            amount = min(raw_limit, config.GLOBAL_MAX_LOAN)
            
    decision = "APPROVED" if amount > 0 else "REJECTED"
    reason_text = "; ".join(reasons) if reasons else "Eligible"
    
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
        
        # Run all 3 Scenarios
        for name, params in config.SCENARIOS.items():
            scenario_result = apply_scenario(row, score, band, name, params)
            row_result.update(scenario_result)
            
        results.append(row_result)

    return pd.DataFrame(results)