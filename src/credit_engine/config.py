# config.py

# Global Constraints (Applied to ALL Scenarios)
# CRITICAL CHANGE: Lowered to 500 to allow micro-loans for mass approval
GLOBAL_MIN_LOAN = 500.0  
GLOBAL_MAX_LOAN = 20000.0

# Score Components (Same logic across scenarios)
WEIGHT_FREQUENCY = 30
WEIGHT_CONSISTENCY = 25
WEIGHT_CAPACITY = 25
WEIGHT_RELIABILITY = 20

# Scoring Reference Values
REF_HIGH_FREQ_MONTHLY = 10      
REF_MAX_VOLATILITY = 1.0

# --- SCENARIO DEFINITIONS ---
SCENARIOS = {
    '1_Strict_Mode': {
        # "The Bank Audit" - Very Safe
        'description': "Conservative. Rejects almost everyone.",
        'min_vends_60d': 5,
        'max_dormancy_days': 21,
        'max_failure_rate': 0.15,
        'limit_strategy': 'Tiered', 
        'tier_caps': {'A': 10000, 'B': 7500, 'C': 5000, 'D': 0},
        'multipliers': {'A': 1.0, 'B': 0.8, 'C': 0.5, 'D': 0.0}
    },
    '2_Balanced_Mode': {
        # "The Learning Curve" - Recommended for V0
        'description': "Moderate. Good balance of risk vs learning.",
        'min_vends_60d': 3,         # Relaxed from 4
        'max_dormancy_days': 45,
        'max_failure_rate': 0.40,   # Increased tolerance
        'limit_strategy': 'Continuous', 
        'multipliers': {'A': 1.0, 'B': 0.8, 'C': 0.6, 'D': 0.0}
    },
    '3_Max_Growth_Mode': {
        # "The Floodgates" - Aiming for 60%+ Approval
        'description': "Aggressive. Approves almost everyone active.",
        'min_vends_60d': 1,         # Just 1 vend makes you eligible!
        'max_dormancy_days': 90,    # 3 months lookback
        'max_failure_rate': 0.80,   # Ignore almost all friction
        'limit_strategy': 'Continuous',
        # We give decent multipliers even to risky bands
        'multipliers': {'A': 1.5, 'B': 1.2, 'C': 0.8, 'D': 0.4} 
    }
}

SCORE_BANDS = {
    'A': 75,  # Easier to get A (was 80)
    'B': 60,  # Easier to get B (was 65)
    'C': 35   # MUCH easier to get C (was 50) - key to mass approval
    # < 35 is Band D
}