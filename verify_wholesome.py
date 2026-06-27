import os
import datetime
from prediction_model import fetch_training_data, train_model
from database import SessionLocal, MatchTrainingData, init_db
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("FOOTBALL_API_KEY")

def verify_wholesome_persistence():
    print("--- Wholesome Persistence Verification ---")
    
    # Initialize Database
    init_db()
    
    # 1. Clear existing test data in MatchTrainingData table
    db = SessionLocal()
    try:
        num_deleted = db.query(MatchTrainingData).delete()
        db.commit()
        print(f"Cleaned {num_deleted} records from match_training_data table.")
    except Exception as e:
        db.rollback()
        print(f"Failed to clean database: {e}")
        return
    finally:
        db.close()

    # 2. Fetch for a single league (EPL - ID: 39)
    print("Fetching training data for EPL (League 39)...")
    league_ids = [39]
    df = fetch_training_data(api_key, league_ids)
    
    if df.empty:
        print("FAIL: No data fetched (check if API key is configured).")
        return

    print(f"SUCCESS: Fetched {len(df)} samples.")
    print("Columns found:", df.columns.tolist())
    
    # 3. Verify Database rows exist
    db = SessionLocal()
    try:
        count = db.query(MatchTrainingData).count()
        if count > 0:
            print(f"SUCCESS: {count} rows created in database.")
        else:
            print("FAIL: No rows created in database.")
            return
    finally:
        db.close()

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

