import os
import datetime
from prediction_model import fetch_training_data, train_model, TRAINING_DATA_FILE
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("RAPIDAPI_KEY")

def verify_wholesome_persistence():
    print("--- Wholesome Persistence Verification ---")
    
    # 1. Clear existing test data if any
    if os.path.exists(TRAINING_DATA_FILE):
        os.remove(TRAINING_DATA_FILE)
        print(f"Cleaned {TRAINING_DATA_FILE}")

    # 2. Fetch for a single league (EPL - ID: 39)
    print("Fetching training data for EPL (League 39)...")
    league_ids = [39]
    df = fetch_training_data(api_key, league_ids)
    
    if df.empty:
        print("FAIL: No data fetched.")
        return

    print(f"SUCCESS: Fetched {len(df)} samples.")
    print("Columns found:", df.columns.tolist())
    
    # 3. Verify CSV exists
    if os.path.exists(TRAINING_DATA_FILE):
        print(f"SUCCESS: {TRAINING_DATA_FILE} created.")
    else:
        print(f"FAIL: {TRAINING_DATA_FILE} NOT created.")
        return

    # 4. Verify Feature Wholesomeness
    required_features = ["home_star_power", "home_motivation", "home_defensive_wall", "h2h_dominance"]
    missing = [f for f in required_features if f not in df.columns]
    if not missing:
        print("SUCCESS: All Beacon Force features present in dataset.")
    else:
        print(f"FAIL: Missing features: {missing}")

    # 5. Test Model Training on this data
    print("Testing ML Trainer on wholesome data...")
    model = train_model(df)
    if model:
        print("SUCCESS: ML Model trained on wholesome features.")
    else:
        print("FAIL: ML Model training failed.")

if __name__ == "__main__":
    verify_wholesome_persistence()
