# my-credit-project/src/credit_engine/config.py

# --- EXISTING CONFIG (Preserved) ---
MIN_TENURE_DAYS = 30
MIN_AVG_MONTHLY_SPEND = 3000.0
MAX_SPEND_VOLATILITY = 0.5
MIN_VEND_FREQUENCY = 3 
STARTING_CREDIT_LIMIT = 1000.0 
ZERO_CREDIT_LIMIT = 0.0

# --- NEW V0 MODEL CONFIG ---

# Global Limits (from your specific instruction)
MIN_LOAN_AMOUNT = 2000.0
MAX_LOAN_AMOUNT = 20000.0

# Step 1: Hard Gates
GATE_MIN_VENDS_60_DAYS = 6      # Insufficient history
GATE_MAX_DAYS_DORMANT = 30      # Dormant behavior

# Step 2: Scoring Weights (Max Points)
WEIGHT_FREQUENCY = 30
WEIGHT_CONSISTENCY = 25
WEIGHT_CAPACITY = 25
WEIGHT_RELIABILITY = 20

# Scoring Reference Values (for normalization)
# e.g., 10 vends/month gets full points for frequency
REF_HIGH_FREQ_MONTHLY = 10      
REF_MAX_VOLATILITY = 1.0        # Lower is better

# Step 3: Score Bands & Caps
# Format: 'Band': {'min_score': X, 'cap': Y, 'k_multiplier': Z}
SCORE_BANDS = {
    'A': {'min_score': 80, 'cap': 10000, 'k': 1.0},
    'B': {'min_score': 65, 'cap': 7500,  'k': 0.8},
    'C': {'min_score': 50, 'cap': 5000,  'k': 0.5},
    'D': {'min_score': 0,  'cap': 0,     'k': 0.0}
}