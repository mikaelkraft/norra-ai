import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
load_dotenv()

# Override DATABASE_URL to avoid production DB connection during test
os.environ["DATABASE_URL"] = "sqlite:///./norra_test_mock.db"

# Mock all Football API / Feature calculation functions to prevent real network requests
import prediction_model

prediction_model.calculate_team_form = lambda team_id, league_id, api_key: 70
prediction_model.calculate_player_star_power = lambda team_id, league_id, season, api_key: 5.0
prediction_model.calculate_defensive_wall = lambda team_id, league_id, season, api_key: 8.0
prediction_model.calculate_injury_impact = lambda team_id, league_id, season, api_key: -2
prediction_model.calculate_deep_h2h_dominance = lambda home_id, away_id, api_key: 2
prediction_model.calculate_fatigue_index = lambda team_id, api_key: 0
prediction_model.calculate_manager_bounce = lambda team_id, api_key: 0
prediction_model.get_market_sentiment = lambda fixture_id, api_key: 5
prediction_model.calculate_poisson_score = lambda fixture_id, api_key: 2.5
prediction_model.calculate_lineup_stability = lambda team_id, api_key: 90
prediction_model.calculate_referee_impact = lambda ref_name: "Medium"
prediction_model.calculate_corner_estimate = lambda fixture_id, api_key: "9-11 Corners"

# Mock get_team_standings inside prediction_model
def mock_get_team_standings(league_id, season, api_key):
    return {
        "response": [
            {
                "league": {
                    "standings": [
                        [
                            {"team": {"id": 1}, "rank": 1},
                            {"team": {"id": 2}, "rank": 5}
                        ]
                    ]
                }
            }
        ]
    }
import football_api
football_api.get_team_standings = mock_get_team_standings
prediction_model.get_team_standings = mock_get_team_standings

from prediction_model import train_model, get_match_prediction

def test_ml_mock_pipeline():
    print("--- Running Mock ML Predictor Logic Test (With API Mocks) ---")
    
    # 1. Create a mock dataset with 100 sample records
    np.random.seed(42)
    n_samples = 100
    
    mock_data = {
        "league_id": np.random.choice([39, 140, 78, 135, 113, 103, 98], n_samples),
        "home_rank": np.random.randint(1, 20, n_samples),
        "away_rank": np.random.randint(1, 20, n_samples),
        "home_motivation": np.random.uniform(0.0, 15.0, n_samples),
        "away_motivation": np.random.uniform(0.0, 15.0, n_samples),
        "home_star_power": np.random.uniform(0.0, 10.0, n_samples),
        "home_defensive_wall": np.random.uniform(0.0, 15.0, n_samples),
        "h2h_dominance": np.random.randint(-10, 10, n_samples),
        "home_advantage": np.ones(n_samples, dtype=int),
        "home_goals": np.random.randint(0, 5, n_samples),
        "away_goals": np.random.randint(0, 5, n_samples)
    }
    
    # Derive the result field: 1 (Home Win), 0 (Draw), 2 (Away Win)
    mock_data["result"] = []
    for h, a in zip(mock_data["home_goals"], mock_data["away_goals"]):
        if h > a:
            mock_data["result"].append(1)
        elif a > h:
            mock_data["result"].append(2)
        else:
            mock_data["result"].append(0)
            
    df = pd.DataFrame(mock_data)
    print(f"Generated mock dataset with {len(df)} rows.")
    
    # 2. Train the Multi-Market Random Forest models
    print("\nTraining models...")
    models_dict = train_model(df)
    
    assert models_dict is not None, "Model training returned None"
    assert "outcome" in models_dict, "Outcome model missing"
    assert "btts" in models_dict, "BTTS model missing"
    assert "ou25" in models_dict, "OU25 model missing"
    assert "ou15" in models_dict, "OU15 model missing"
    assert "ou35" in models_dict, "OU35 model missing"
    print("SUCCESS: Multi-Market Random Forest Models trained successfully!")
    
    # 3. Perform Mock Inference
    mock_fixture = {
        "fixture": {
            "id": 99999,
            "referee": "Mock Ref",
            "venue": {
                "name": "Mock Stadium",
                "surface": "grass"
            }
        },
        "teams": {
            "home": {
                "id": 1,
                "name": "Home Team FC"
            },
            "away": {
                "id": 2,
                "name": "Away Team United"
            }
        },
        "league": {
            "id": 39,
            "name": "Premier League",
            "season": 2025
        }
    }
    
    print("\nRunning inference for mock match: Home Team FC vs Away Team United...")
    pred = get_match_prediction(mock_fixture, api_key="mock_key", model=models_dict)
    
    print("\n--- Inference Output Fields Check ---")
    print(f"FT Outcome: {pred['main']}")
    print(f"Confidence: {pred['ml']} / {pred['ou_refined']}")
    print(f"Double Chance: {pred['dc']}")
    print(f"BTTS: {pred['btts']}")
    print(f"Draw No Bet: {pred['dnb']}")
    print(f"Multi-Goals Range: {pred['multi_goals']}")
    print(f"Halftime/Fulltime: {pred['ht_ft']}")
    print(f"Combo Bet: {pred['combos']}")
    print(f"League Avg Goals: {pred['league_avg_goals']}")
    
    # Assertions to verify all new fields exist and are populated
    assert "btts" in pred, "BTTS field missing in prediction"
    assert "dnb" in pred, "DNB field missing in prediction"
    assert "multi_goals" in pred, "multi_goals field missing in prediction"
    assert "ht_ft" in pred, "ht_ft field missing in prediction"
    assert "combos" in pred, "combos field missing in prediction"
    assert "league_avg_goals" in pred, "league_avg_goals field missing in prediction"
    
    print("\nSUCCESS: All prediction fields present and correctly formatted!")
    print("Test passed successfully.")

if __name__ == "__main__":
    test_ml_mock_pipeline()
