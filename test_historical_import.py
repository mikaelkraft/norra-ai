# test_historical_import.py
import os
from dotenv import load_dotenv
load_dotenv()

import database
from database import SessionLocal, MatchTrainingData
from prediction_model import fetch_football_data_co_uk_historical, load_training_data

def run_test():
    print("--- Starting Historical Import Test ---")
    
    # 1. Initialize local SQLite DB for testing
    database.init_db()
    
    db = SessionLocal()
    try:
        # Check current count of samples
        initial_count = db.query(MatchTrainingData).count()
        print(f"Initial training samples in local DB: {initial_count}")
        
        # We will test importing Swedish Allsvenskan (ID: 113)
        print("\nRunning historical import for Sweden Allsvenskan (ID: 113)...")
        success = fetch_football_data_co_uk_historical(113)
        
        if success:
            print("Import function returned success!")
            
            # Check count after import
            final_count = db.query(MatchTrainingData).count()
            print(f"Final training samples in local DB: {final_count}")
            print(f"Added {final_count - initial_count} samples.")
            
            # Load training data and check columns
            df = load_training_data()
            print("\nLoaded training DataFrame:")
            print("Shape:", df.shape)
            print("Columns:", df.columns.tolist())
            print("\nSample records:")
            print(df.head(3))
            
            assert not df.empty, "DataFrame should not be empty!"
            assert "result" in df.columns, "DataFrame must contain target column 'result'"
            print("\n[SUCCESS] Verification Test Passed successfully!")
        else:
            print("[FAIL] Import function returned failure.")
            
    except Exception as e:
        print(f"[ERROR] Test encountered an error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
