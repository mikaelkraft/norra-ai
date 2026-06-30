import os
import sys
import datetime
import database
from database import SessionLocal, PlayedMatch, Prediction
from prediction_model import (
    fetch_football_data_co_uk_historical,
    fetch_training_data,
    train_model,
    get_match_prediction,
    get_local_standings,
    get_local_form,
    get_local_h2h,
    get_local_team_stats
)
from Norra import verify_previous_matches

def main():
    print("--- Running Norra AI Verification Test Script ---")
    
    # 1. Init DB
    print("\n[Step 1] Initializing database...")
    database.init_db()
    
    # 2. Seed Sweden (League 113)
    print("\n[Step 2] Seeding Sweden Allsvenskan (League 113) historical played matches...")
    try:
        fetch_football_data_co_uk_historical(113)
    except Exception as e:
        print(f"Warning: Seeding request failed ({e}). Checking if database already has matches...")
        
    db = SessionLocal()
    played_count = db.query(PlayedMatch).filter(PlayedMatch.league_id == 113).count()
    if played_count == 0:
        print("[FAIL] Database has no played matches for League 113 and seeding failed. Exiting.")
        sys.exit(1)
        
    print(f"[SUCCESS] Found {played_count} Sweden played matches in the local database.")
    
    # 3. Retrieve some team names from the DB to test calculations
    sample_match = db.query(PlayedMatch).filter(PlayedMatch.league_id == 113).first()
    if not sample_match:
        print("[FAIL] No played matches found in database. Exiting.")
        sys.exit(1)
        
    home_team = sample_match.home_team
    away_team = sample_match.away_team
    season = sample_match.season
    print(f"\n[Step 3] Running local stats calculations for: {home_team} vs {away_team} (Season {season})")
    
    standings = get_local_standings(113, season)
    home_rank = standings.get(home_team, 10)
    away_rank = standings.get(away_team, 10)
    print(f"  Rankings: {home_team} (Rank {home_rank}), {away_team} (Rank {away_rank})")
    
    home_form = get_local_form(home_team, 113)
    away_form = get_local_form(away_team, 113)
    print(f"  Form: {home_team} (Form {home_form}/100), {away_team} (Form {away_form}/100)")
    
    h2h = get_local_h2h(home_team, away_team, 113)
    print(f"  H2H Dominance: {h2h}")
    
    home_star, home_def = get_local_team_stats(home_team, 113, season)
    print(f"  Team Stats: {home_team} (Star Power: {home_star:.2f}, Def Wall: {home_def:.2f})")
    
    # 4. Train Model
    print("\n[Step 4] Training the ML model on local DB data...")
    train_df = fetch_training_data(None, [113])
    model = train_model(train_df)
    print("[SUCCESS] Model trained successfully.")
    
    # 4.5 Test Model Cache (Pickle)
    print("\n[Step 4.5] Testing Model Cache (Pickling)...")
    from prediction_model import save_cached_model, load_cached_model
    try:
        # Remove any existing cache file
        if os.path.exists("model.pkl"):
            os.remove("model.pkl")
            
        save_cached_model(model)
        if not os.path.exists("model.pkl"):
            raise FileNotFoundError("model.pkl was not created on disk.")
            
        loaded_model = load_cached_model()
        if not loaded_model:
            raise ValueError("Failed to load cached model from disk.")
            
        print("[SUCCESS] Model caching and loading verified successfully!")
    except Exception as cache_err:
        print(f"[FAIL] Model caching failed: {cache_err}")
        sys.exit(1)
    
    # 5. Test get_match_prediction with a mock fixture
    print("\n[Step 5] Testing prediction generation with a mock fixture...")
    try:
        season_int = int(season.split("/")[0]) if "/" in season else int(season)
    except ValueError:
        season_int = 2025
        
    mock_fixture = {
        "fixture": {
            "id": 999999,
            "venue": {
                "name": "Swedbank Stadion",
                "city": "Malmo"
            },
            "weather": {
                "description": "clear sky",
                "temp": 18
            },
            "referee": "Glenn Nyberg"
        },
        "teams": {
            "home": {
                "id": 1001,
                "name": home_team
            },
            "away": {
                "id": 1002,
                "name": away_team
            }
        },
        "league": {
            "id": 113,
            "name": "Allsvenskan",
            "season": season_int
        }
    }
    
    prediction = get_match_prediction(mock_fixture, None, model=model)
    print(f"[SUCCESS] Prediction generated successfully!")
    print(f"  Main: {prediction['main']}")
    print(f"  Confidence: {prediction['confidence']}")
    print(f"  Double Chance: {prediction['dc']}")
    print(f"  Halftime Prediction: {prediction['ht']}")
    print(f"  BTTS: {prediction['btts']}")
    print(f"  Over/Under Refined: {prediction['ou_refined']}")
    print(f"  Draw No Bet: {prediction['dnb']}")
    print(f"  Combo: {prediction['combos']}")
    print(f"  H2H Dominance: {prediction['h2h_dom']}")
    
    # 6. Test verify_previous_matches by inserting a mock prediction
    print("\n[Step 6] Testing offline match outcome verification...")
    # Clean any old mock prediction
    db.query(Prediction).filter(Prediction.fixture_id == 999999).delete()
    
    # Create prediction record
    pred_rec = Prediction(
        fixture_id=999999,
        home_team=home_team,
        away_team=away_team,
        league_name="Allsvenskan",
        prediction_main=prediction["main"],
        confidence=prediction["confidence"],
        dc=prediction["dc"],
        ht=prediction["ht"],
        ou_refined=prediction["ou_refined"],
        star_power=prediction["star_power"],
        h2h_dom=prediction["h2h_dom"],
        btts=prediction["btts"],
        dnb=prediction["dnb"],
        multi_goals=prediction["multi_goals"],
        ht_ft=prediction["ht_ft"],
        combos=prediction["combos"],
        league_avg_goals=2.5,
        created_at=datetime.datetime.utcnow()
    )
    db.add(pred_rec)
    db.commit()
    
    # Add to bot_stats json
    import json
    stats_file = "bot_stats.json"
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            stats = json.load(f)
    else:
        stats = {}
    stats.setdefault('predictions_to_verify', {})
    
    actual_res = "Home" if sample_match.home_goals > sample_match.away_goals else ("Away" if sample_match.away_goals > sample_match.home_goals else "Draw")
    stats['predictions_to_verify']["999999"] = actual_res
    
    with open(stats_file, 'w') as f:
        json.dump(stats, f)
        
    print("  Triggering verify_previous_matches...")
    verify_previous_matches(None)
    
    # Clean up mock prediction
    db.query(Prediction).filter(Prediction.fixture_id == 999999).delete()
    db.commit()
    db.close()
    
    print("\n--- Norra AI Verification Test Complete: ALL TESTS PASSED! ---")

if __name__ == "__main__":
    main()
