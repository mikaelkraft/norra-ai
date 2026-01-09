import os
import datetime
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from football_api import get_prioritized_fixtures, get_fixtures
from Norra import generate_predictions, post_predictions, fetch_predictions

def test_full_pipeline():
    api_key = os.getenv("RAPIDAPI_KEY")
    print("--- Testing Full ML + Prediction Pipeline ---")
    
    # 1. Test Standings Lookup
    from football_api import get_team_standings
    print("\n[V] Testing Standings Fetch (Premier League 2025)...")
    standings = get_team_standings(39, 2025, api_key)
    if standings and standings.get('response'):
        print("Standings fetch: SUCCESS")
    else:
        print("Standings fetch: FAILED or empty response")

    # 2. Test Training Data Fetch
    from prediction_model import fetch_training_data, train_model
    print("\n[V] Testing Historical Data Fetch & Training (subset)...")
    # Just one league for speed
    train_df = fetch_training_data(api_key, [39]) 
    print(f"Training DF shape: {train_df.shape if not train_df.empty else 'EMPTY'}")
    
    model = train_model(train_df)
    if model:
        print("Model Training: SUCCESS")
    else:
        print("Model Training: FAILED")

    # 3. Test Live Prediction Generation
    print("\n[V] Testing Live Prediction Generation (Premier League)...")
    fixtures = get_fixtures(api_key, league_id=39, season=2025, next_n=1)
    if not fixtures:
        print("No EPL fixtures found. Using prioritized fallback...")
        fixtures = get_prioritized_fixtures(datetime.datetime.now().date(), api_key)
        
    if fixtures:
        test_fixture = fixtures[:1]
        preds = generate_predictions(test_fixture, api_key, model=model)
        for match, data in preds.items():
            print(f"\nMatch: {match}")
            print(f"Logic: {data['detailed']}")
            print(f"Outcome: {data['winner']} ({data['confidence']})")
            print(f"GG: {data['gg']} | O/U: {data['ou']}")
            
            # Print the final tweet format
            tweet = (
                f"🏆 NorraAI Prediction\n"
                f"⚽ Match: {data['home']} vs {data['away']}\n"
                f"🔮 Logic: {data['detailed']}\n"
                f"💎 GG/NG: {data['gg']} | O/U: {data['ou']}\n"
                f"💡 Outcome: {data['winner']} ({data['confidence']})\n"
                f"📣 Stats: {data['advice']}\n\n"
                f"NorraAI Football Predictions"
            )
            print("-" * 30)
            print(tweet)
            print("-" * 30)
    else:
        print("No matches found for live test.")

if __name__ == "__main__":
    test_full_pipeline()
