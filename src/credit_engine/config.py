# config.py

# Global Constraints (Applied to ALL Scenarios)
# CRITICAL CHANGE: Lowered to 100 to allow micro-loans for mass approval (layman: "Starting Small")
GLOBAL_MIN_LOAN = 100.0  
GLOBAL_MAX_LOAN = 50000.0

# Score Components (Same logic across scenarios)
WEIGHT_FREQUENCY = 30
WEIGHT_CONSISTENCY = 25
WEIGHT_CAPACITY = 25
WEIGHT_RELIABILITY = 20

# Scoring Reference Values
REF_HIGH_FREQ_MONTHLY = 10      
REF_MAX_VOLATILITY = 1.0

# --- SCENARIO DEFINITIONS (LAYMAN NAMING) ---
SCENARIOS = {
    '1_Conservative_Bank': {
        # OLD: Strict Mode
        'description': "Strict. Only for the perfect customers.",
        'min_vends_60d': 5,
        'max_dormancy_days': 21,
        'max_failure_rate': 0.15,
        'soft_failure_threshold': 0.10, # Penalty if above this
        'soft_dormancy_threshold': 14,  # Penalty if above this
        'limit_strategy': 'Tiered', 
        'tier_caps': {'A': 10000, 'B': 7500, 'C': 5000, 'D': 0},
        'multipliers': {'A': 1.0, 'B': 0.8, 'C': 0.5, 'D': 0.0}
    },
    '2_Balanced_Growth': {
        # OLD: Balanced Mode
        'description': "Balanced. Good for standard growth.",
        'min_vends_60d': 3,         
        'max_dormancy_days': 45,
        'max_failure_rate': 0.50,
        'soft_failure_threshold': 0.30, 
        'soft_dormancy_threshold': 30,
        'limit_strategy': 'Continuous', 
        'multipliers': {'A': 1.2, 'B': 1.0, 'C': 0.7, 'D': 0.0}
    },
    '3_Mass_Adoption': {
        # OLD: Max Growth Mode -> TARGETING 60%+ APPROVAL
        'description': "Aggressive. Open the floodgates.",
        'min_vends_60d': 1,         # As long as they have used it once recently
        'max_dormancy_days': 120,   # 4 months lookback (very loose)
        'max_failure_rate': 1.0,    # Ignore failure rates completely for eligibility
        'soft_failure_threshold': 0.60, # But penalize limit if it's really bad
        'soft_dormancy_threshold': 60,  # Penalize limit if dormant > 2 months
        'limit_strategy': 'Continuous',
        # Give riskier bands a chance, but with smaller multipliers
        'multipliers': {'A': 2.0, 'B': 1.5, 'C': 1.0, 'D': 0.5} 
    }
}

SCORE_BANDS = {
    # Relaxed bands to push people from D (Reject) to C (Approve)
    'A': 70,  # Easy A
    'B': 50,  # Very Easy B
    'C': 20   # "If you have a pulse" -> Band C
    # < 20 is Band D
}