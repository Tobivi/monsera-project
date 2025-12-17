# config.py

# Global Constraints (Applied to ALL Scenarios)
GLOBAL_MIN_LOAN = 2000.0
GLOBAL_MAX_LOAN = 20000.0

# Score Components (Same logic across scenarios, just different eligibility)
WEIGHT_FREQUENCY = 30
WEIGHT_CONSISTENCY = 25
WEIGHT_CAPACITY = 25
WEIGHT_RELIABILITY = 20
REF_HIGH_FREQ_MONTHLY = 10      
REF_MAX_VOLATILITY = 1.0

# --- SCENARIO DEFINITIONS ---
SCENARIOS = {
    'A_Conservative': {
        # The Original "Tight" Rules
        'min_vends_60d': 6,
        'max_dormancy_days': 30,
        'max_failure_rate': 0.20,   # Strict on failures
        'limit_strategy': 'Tiered', # Fixed Caps
        'tier_caps': {'A': 10000, 'B': 7500, 'C': 5000, 'D': 0},
        'multipliers': {'A': 1.0, 'B': 0.8, 'C': 0.5, 'D': 0}
    },
    'B_Moderate': {
        # The "Learning" Rules (Recommended)
        'min_vends_60d': 4,         # Relaxed
        'max_dormancy_days': 45,    # Relaxed
        'max_failure_rate': 0.35,   # Tolerates more retry noise
        'limit_strategy': 'Continuous', # No hard band caps, just multipliers
        # Multipliers determine % of Median Spend we advance
        'multipliers': {'A': 1.0, 'B': 0.75, 'C': 0.50, 'D': 0} 
    },
    'C_Aggressive': {
        # The "Growth" Rules (Maximum Approval)
        'min_vends_60d': 3,         # Very Relaxed
        'max_dormancy_days': 60,    # Very Relaxed
        'max_failure_rate': 0.50,   # High friction tolerance
        'limit_strategy': 'Continuous',
        # Aggressive multipliers (can lend MORE than median for top users)
        'multipliers': {'A': 1.2, 'B': 1.0, 'C': 0.75, 'D': 0} 
    }
}

SCORE_BANDS = {
    'A': 80,
    'B': 65,
    'C': 50
}