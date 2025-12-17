# config.py

# Global Constraints
GLOBAL_MIN_LOAN = 100.0  
GLOBAL_MAX_LOAN = 50000.0

# Score Components
WEIGHT_FREQUENCY = 30
WEIGHT_CONSISTENCY = 25
WEIGHT_CAPACITY = 25
WEIGHT_RELIABILITY = 20

REF_HIGH_FREQ_MONTHLY = 10      
REF_MAX_VOLATILITY = 1.0

# --- SCENARIO DEFINITIONS ---
SCENARIOS = {
    '1_Conservative_Bank': {
        'description': "Strict. Only for the perfect customers.",
        'min_vends_60d': 5,
        'max_dormancy_days': 21,
        'max_failure_rate': 0.15,
        'soft_failure_threshold': 0.10, 
        'soft_dormancy_threshold': 14, 
        # UPDATED: Changed from Tiered to Continuous to allow variance
        'limit_strategy': 'Continuous', 
        'multipliers': {'A': 0.8, 'B': 0.6, 'C': 0.4, 'D': 0.0} 
    },
    '2_Balanced_Growth': {
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
        'description': "Aggressive. Open the floodgates.",
        'min_vends_60d': 1,        
        'max_dormancy_days': 120,   
        'max_failure_rate': 1.0,    
        'soft_failure_threshold': 0.60, 
        'soft_dormancy_threshold': 60,  
        'limit_strategy': 'Continuous',
        # Higher multipliers for mass adoption
        'multipliers': {'A': 2.0, 'B': 1.5, 'C': 1.0, 'D': 0.5} 
    }
}

SCORE_BANDS = {
    'A': 70,  
    'B': 50,  
    'C': 20   
}