# scripts/run_batch.py
import sys
import os
import pandas as pd

# Add the project root to the python path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Updated imports based on your folder structure
from src.etl.loader import load_and_clean_data
from src.etl.transformer import calculate_features
from src.credit_engine.scoring import apply_v0_rules

def main():
    # 1. Define File Path
    # Pointing to the 'data' folder relative to the script
    file_path = os.path.join(os.path.dirname(__file__), '../data/Draft Data from Val.csv')

    # 2. Pipeline Execution
    try:
        # Step A: Load
        print(f"Reading data from: {file_path}")
        raw_df = load_and_clean_data(file_path)
        
        # Step B: Feature Engineering (Now includes V0 metrics)
        features_df = calculate_features(raw_df)
        
        # Step C: Scoring (Now includes Gates, Bands, and Limits)
        scorecard = apply_v0_rules(features_df)

        # 3. Output Results
        print("\n--- SCORING RESULTS (SAMPLE) ---")
        # Display new columns: Score, Band, Approved Amount
        print(scorecard[['Meter No', 'Score', 'Band', 'Decision', 'Approved Amount', 'Reason']].head())

        # Save to CSV
        output_filename = 'monsera_v0_credit_decisions.csv'
        scorecard.to_csv(output_filename, index=False)
        print(f"\nFull results saved to {output_filename}")

    except FileNotFoundError:
        print("Error: Could not find the dataset file. Check that 'Draft Data from Val.csv' is in the 'data' folder.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()