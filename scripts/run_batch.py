# main.py
import pandas as pd
from data_loader import load_and_clean_data
from feature_engineering import calculate_features
from scoring_engine import apply_v0_rules

def main():
    # 1. Define File Path
    # Make sure 'Draft Data from Val.csv' is in the same folder
    file_path = 'Draft Data from Val.csv'

    # 2. Pipeline Execution
    try:
        # Step A: Load
        raw_df = load_and_clean_data(file_path)
        
        # Step B: Feature Engineering
        features_df = calculate_features(raw_df)
        
        # Step C: Scoring
        scorecard = apply_v0_rules(features_df)

        # 3. Output Results
        print("\n--- SCORING RESULTS (SAMPLE) ---")
        print(scorecard.head())

        # Save to CSV for the team
        output_filename = 'monsera_v0_credit_decisions.csv'
        scorecard.to_csv(output_filename, index=False)
        print(f"\nFull results saved to {output_filename}")

    except FileNotFoundError:
        print("Error: Could not find the dataset file. Please check the filename.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()