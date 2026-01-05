# prediction_model.py

# Import necessary libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from football_api import fetch_team_data
import datetime
import os
from dotenv import load_dotenv
from football_api import get_fixtures

load_dotenv()

def fetch_and_prepare_data(api_key, league_ids):
    all_data = []
    
    for league_id in league_ids:
        # Season 2025 for current data
        fixtures_data = get_fixtures(api_key, league_id=league_id, date=datetime.datetime.now().date(), season=2025)
        if fixtures_data:
            league_data = process_fixtures_data(fixtures_data)
            all_data.extend(league_data)

    return pd.DataFrame(all_data)

def process_fixtures_data(fixtures_data):
    processed_data = []

    for fixture in fixtures_data:
        home_team = fixture.get("teams", {}).get("home", {}).get("name", "Home")
        away_team = fixture.get("teams", {}).get("away", {}).get("name", "Away")
        
        # We need historical results to train. For current fixtures, result is 0.
        # In a real training scenario, we'd fetch past fixtures.
        goals_home = fixture.get("goals", {}).get("home")
        goals_away = fixture.get("goals", {}).get("away")
        
        if goals_home is not None and goals_away is not None:
            result = 1 if goals_home > goals_away else (2 if goals_away > goals_home else 0)
            data_point = {
                "home_id": fixture['teams']['home']['id'],
                "away_id": fixture['teams']['away']['id'],
                "result": result
            }
            processed_data.append(data_point)

    return processed_data

def train_model(df):
    if df.empty:
        print("No data to train on.")
        return None
        
    # Extract features and labels
    features = df.drop(columns=['result'])
    labels = df['result']

    # Train the Random Forest Classifier
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(features, labels)

    return model

def calculate_team_form(team_id, league_id, api_key):
    """
    Calculates a form score (0-100) based on the last 5 matches.
    Wins = 20 pts, Draws = 10 pts, Losses = 0 pts.
    """
    from football_api import get_fixtures
    # Fetch last 5 matches for this team
    fixtures = get_fixtures(api_key, team_id=team_id, last_n=5)
    
    if not fixtures:
        return 50 # Average form if no data
        
    score = 0
    for fixture in fixtures:
        goals = fixture.get('goals', {})
        teams = fixture.get('teams', {})
        
        is_home = teams.get('home', {}).get('id') == team_id
        home_goals = goals.get('home', 0)
        away_goals = goals.get('away', 0)
        
        if home_goals == away_goals:
            score += 10 # Draw
        elif is_home and home_goals > away_goals:
            score += 20 # Win
        elif not is_home and away_goals > home_goals:
            score += 20 # Win
            
    return score

def get_match_prediction(fixture, api_key):
    """
    Calculates a prediction based on form, H2H, and venue.
    """
    home_id = fixture['teams']['home']['id']
    away_id = fixture['teams']['away']['id']
    league_id = fixture['league']['id']
    
    home_form = calculate_team_form(home_id, league_id, api_key)
    away_form = calculate_team_form(away_id, league_id, api_key)
    
    # Simple weighted logic
    # Home advantage: +10%
    home_score = home_form + 10
    away_score = away_form
    
    if home_score > away_score + 15:
        return f"{fixture['teams']['home']['name']} Win"
    elif away_score > home_score + 15:
        return f"{fixture['teams']['away']['name']} Win"
    else:
        return "Draw / Close Match"

def evaluate_model(model, test_data):
    # Function to evaluate the model's performance
    # Add logic to evaluate the model's performance on a test data set

    return model_performance  # Return the model's performance metrics
def make_predictions(model, fixtures, api_key):
    """
    Inference layer: Uses the trained model or the custom rule-engine
    to generate match outcomes.
    """
    predictions = {}
    for fixture in fixtures:
        fixture_id = fixture['fixture']['id']
        # For the ML model, we'd feed form scores to .predict()
        # For the prompt logic, we use our refined get_match_prediction
        prediction = get_match_prediction(fixture, api_key)
        predictions[fixture_id] = prediction
    
    return predictions

def main():
    api_key = os.getenv("RAPIDAPI_KEY")
    current_date = datetime.datetime.now().date()
    
    from football_api import get_prioritized_fixtures
    fixtures = get_prioritized_fixtures(current_date, api_key)
    
    if not fixtures:
        print("No matches to predict today.")
        return
        
    # We use our refined prediction engine
    predictions = make_predictions(None, fixtures, api_key)
    
    print("\n--- Match Predictions ---")
    for fid, pred in predictions.items():
        print(f"Fixture {fid}: {pred}")

if __name__ == "__main__":
    main()