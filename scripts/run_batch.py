import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.etl.loader import load_and_clean_data
from src.etl.transformer import calculate_features
from src.credit_engine.scoring import apply_v0_rules

def main():
    file_path = os.path.join(os.path.dirname(__file__), '../data/consolidated_transactions.csv')

    try:
        print(f"Reading data from: {file_path}")
        raw_df = load_and_clean_data(file_path)
        
        features_df = calculate_features(raw_df)
        scorecard = apply_v0_rules(features_df)

        print("\n--- COMPARISON (SAMPLE) ---")
        cols = ['Meter No', 'Score', 'Median_Spend', 
                'Decision_A_Conservative', 'Amount_A_Conservative',
                'Decision_B_Moderate', 'Amount_B_Moderate',
                'Decision_C_Aggressive', 'Amount_C_Aggressive']
        
        # Handle case where fewer cols exist if config changed, but usually fine
        print(scorecard[cols].head())

        output_filename = 'monsera_v0_scenario_analysis.csv'
        scorecard.to_csv(output_filename, index=False)
        print(f"\nFull scenario analysis saved to {output_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()