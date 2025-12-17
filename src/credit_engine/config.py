# config.py

# Global Constraints (Applied to ALL Scenarios)
GLOBAL_MIN_LOAN = 1500.0  # Lowered slightly to capture the small "Band D" loans
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
        'min_vends_60d': 5,         # Test < 5
        'max_dormancy_days': 21,    # Test > 21 days
        'max_failure_rate': 0.15,   # Strict friction check
        'limit_strategy': 'Tiered', 
        'tier_caps': {'A': 10000, 'B': 7500, 'C': 5000, 'D': 0},
        'multipliers': {'A': 1.0, 'B': 0.8, 'C': 0.5, 'D': 0.0} # Band D is REJECTED
    },
    '2_Balanced_Mode': {
        # "The Learning Curve" - Recommended for V0
        'description': "Moderate. Good balance of risk vs learning.",
        'min_vends_60d': 4,         # Test < 4
        'max_dormancy_days': 45,    # Test > 45 days
        'max_failure_rate': 0.35,   # Tolerates some failures
        'limit_strategy': 'Continuous', 
        'multipliers': {'A': 1.0, 'B': 0.8, 'C': 0.6, 'D': 0.0} # Band D is still REJECTED
    },
    '3_Max_Growth_Mode': {
        # "The Floodgates" - Aiming for 60%+ Approval
        'description': "Aggressive. Approves almost everyone active.",
        'min_vends_60d': 2,         # Test < 3 (Approves 2 vends)
        'max_dormancy_days': 60,    # Test > 60 days
        'max_failure_rate': 0.60,   # High friction tolerance
        'limit_strategy': 'Continuous',
        # CRITICAL CHANGE: We lend to Band D (Low Score) users!
        # They get a small limit (25% of median) instead of a rejection.
        'multipliers': {'A': 1.5, 'B': 1.2, 'C': 0.8, 'D': 0.25} 
    }
}

SCORE_BANDS = {
    'A': 80,
    'B': 65,
    'C': 50
    # < 50 is Band D
}