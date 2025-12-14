# scoring_engine.py
import pandas as pd
import config

def apply_v0_rules(features_df):
    """
    Applies the deterministic V0 logic to approve/reject credit.
    Reference PRD: V0: The Heuristic Cold Start [cite: 78]
    """
    print("Running V0 Rule Engine...")

    results = []

    for meter_id, row in features_df.iterrows():
        # Retrieve metrics
        tenure = row['tenure_days']
        avg_spend = row['avg_monthly_spend']
        volatility = row['volatility']
        frequency = row['total_vends']

        # RULE EVALUATION 
        # Condition 1: Is the relationship long enough? (Stability)
        is_stable_tenure = tenure >= config.MIN_TENURE_DAYS
        
        # Condition 2: Do they spend enough to justify a loan? (Capacity)
        is_sufficient_spend = avg_spend >= config.MIN_AVG_MONTHLY_SPEND
        
        # Condition 3: Is their spending consistent? (Risk)
        is_low_volatility = volatility <= config.MAX_SPEND_VOLATILITY
        
        # Condition 4: Do we have enough data points?
        is_frequent_user = frequency >= config.MIN_VEND_FREQUENCY

        # DECISION LOGIC
        if is_stable_tenure and is_sufficient_spend and is_low_volatility and is_frequent_user:
            decision = "APPROVED"
            credit_limit = config.STARTING_CREDIT_LIMIT
            reason = "Passes all V0 criteria"
        else:
            decision = "REJECTED"
            credit_limit = config.ZERO_CREDIT_LIMIT
            
            # Generate Reason Codes for rejection 
            reasons = []
            if not is_stable_tenure: reasons.append(f"Tenure too short ({tenure} days)")
            if not is_sufficient_spend: reasons.append(f"Low avg spend (N{avg_spend:.2f})")
            if not is_low_volatility: reasons.append(f"High volatility ({volatility:.2f})")
            if not is_frequent_user: reasons.append("Insufficient transaction history")
            reason = "; ".join(reasons)

        results.append({
            'Meter No': meter_id,
            'Tenure (Days)': tenure,
            'Avg Monthly Spend': round(avg_spend, 2),
            'Volatility': round(volatility, 2),
            'Vends Count': frequency,
            'Decision': decision,
            'Credit Limit': credit_limit,
            'Reason': reason
        })

    return pd.DataFrame(results)