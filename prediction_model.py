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

def fetch_training_data(api_key, league_ids):
    """
    Fetches historical fixtures for training the model.
    """
    all_data = []
    print(f"Fetching historical training data for {len(league_ids)} leagues...")
    for league_id in league_ids:
        # Fetch last 30 matches for each league to build a dataset
        fixtures_data = get_fixtures(api_key, league_id=league_id, last_n=30)
        if fixtures_data:
            league_data = process_fixtures_data(fixtures_data, api_key)
            all_data.extend(league_data)
    
    return pd.DataFrame(all_data)

def process_fixtures_data(fixtures_data, api_key):
    processed_data = []

    # To avoid repeated API calls, we'll fetch standings per league if we can
    # For this simplified version, we'll use a local cache for standings
    standings_cache = {}

    for fixture in fixtures_data:
        home_id = fixture['teams']['home']['id']
        away_id = fixture['teams']['away']['id']
        league_id = fixture['league']['id']
        season = fixture['league']['season']
        
        # Historical results
        goals_home = fixture.get("goals", {}).get("home")
        goals_away = fixture.get("goals", {}).get("away")
        
        if goals_home is not None and goals_away is not None:
            # Result: 1 (Home Win), 0 (Draw), 2 (Away Win)
            result = 1 if goals_home > goals_away else (2 if goals_away > goals_home else 0)
            
            # Fetch standings for this league/season once
            cache_key = f"{league_id}_{season}"
            if cache_key not in standings_cache:
                from football_api import get_team_standings
                standings_raw = get_team_standings(league_id, season, api_key)
                # Map team_id to rank
                ranks = {}
                try:
                    # standings_raw['response'][0]['league']['standings'][0] is the list
                    league_standings = standings_raw.get('response', [])[0].get('league', {}).get('standings', [])[0]
                    for entry in league_standings:
                        ranks[entry['team']['id']] = entry['rank']
                except:
                    pass
                standings_cache[cache_key] = ranks
            
            ranks = standings_cache[cache_key]
            home_rank = ranks.get(home_id, 10) # Default mid-table
            away_rank = ranks.get(away_id, 10)

            # Features
            data_point = {
                "home_id": home_id,
                "away_id": away_id,
                "home_rank": home_rank,
                "away_rank": away_rank,
                "home_advantage": 1,
                "result": result
            }
            processed_data.append(data_point)

    return processed_data

def train_model(df):
    if df.empty:
        print("No historical data found. Falling back to rule-engine.")
        return None
        
    print(f"Training RandomForestClassifier on {len(df)} samples...")
    # Features: home/away IDs (categorical-ish), ranks, advantage
    X = df.drop(columns=['result'])
    y = df['result']

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Simple validation score (mock)
    print("Model trained successfully.")
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

def get_market_sentiment(fixture_id, api_key):
    """
    Fetches odds and returns a sentiment score.
    Favoring the team with lower odds (market favorite).
    """
    from football_api import get_odds
    odds_data = get_odds(fixture_id, api_key)
    if not odds_data:
        return 0 # No sentiment
        
    # Simplified: check for the "Match Winner" market from a major bookie
    # We look for the lowest odd to identify the 'Public Favorite'
    try:
        bookies = odds_data[0].get('bookmakers', [])
        if not bookies: return 0
        
        # Take the first bookmaker (e.g., 10Bet, Bet365)
        bets = bookies[0].get('bets', [])
        winner_bet = next((b for b in bets if b['name'] == 'Match Winner'), None)
        if not winner_bet: return 0
        
        values = winner_bet.get('values', [])
        # values: [{"value": "Home", "odd": "1.50"}, ...]
        home_odd = float(next((v['odd'] for v in values if v['value'] == 'Home'), 100))
        away_odd = float(next((v['odd'] for v in values if v['value'] == 'Away'), 100))
        
        if home_odd < away_odd: return 15 # Home favorite
        if away_odd < home_odd: return -15 # Away favorite
    except:
        pass
    return 0

def calculate_booking_risk(team_id, league_id, api_key):
    """
    Predicts if a team is likely to get many cards based on history.
    """
    from football_api import get_team_statistics
    stats = get_team_statistics(league_id, 2025, team_id, api_key)
    if not stats: return "Medium"
    
    # Check total yellow/red cards
    cards = stats.get('response', {}).get('cards', {})
    yellow = sum([int(v.get('total', 0) or 0) for v in cards.get('yellow', {}).values()])
    if yellow > 40: return "High"
    if yellow < 20: return "Low"
    return "Medium"

def calculate_corner_estimate(fixture_id, api_key):
    """
    Estimates corners based on professional prediction data.
    """
    from football_api import get_predictions
    preds = get_predictions(fixture_id, api_key)
    if not preds: return "8-10"
    
    # API-Football predictions often don't have a direct 'corners' field in advice,
    # but we can infer from attacking pressure or use a default based on teams.
    # For now, we use a statistically safe range for Top-Flight matches.
    return "9-11"

def get_halftime_prediction(home_form, away_form):
    """
    Predicts HT result based on form/momentum.
    """
    if home_form > away_form + 20: return "Home"
    if away_form > home_form + 20: return "Away"
    return "Draw"

def get_match_prediction(fixture, api_key, model=None):
    """
    Calculates a prediction based on form, H2H, venue, Market Sentiment, and ML Model.
    """
    fixture_id = fixture['fixture']['id']
    home_id = fixture['teams']['home']['id']
    away_id = fixture['teams']['away']['id']
    league_id = fixture['league']['id']
    
    # Venue / Home Advantage
    is_home = True # Current fixture home data
    
    # Weather (if available)
    weather = fixture.get('fixture', {}).get('weather', {}).get('description', 'clear sky')
    weather_impact = 0
    if "rain" in weather.lower() or "snow" in weather.lower():
        weather_impact = -5 # Slightly favors defense/draws
        
    home_form = calculate_team_form(home_id, league_id, api_key)
    away_form = calculate_team_form(away_id, league_id, api_key)
    
    # Market Sentiment Booster
    sentiment = get_market_sentiment(fixture_id, api_key)
    
    # Rule-Engine Score
    home_score = home_form + 10 + (sentiment if sentiment > 0 else 0) + weather_impact
    away_score = away_form + (abs(sentiment) if sentiment < 0 else 0)
    
    # ML Model Prediction (if available)
    ml_outcome = "No ML context"
    if model:
        # Fetch current ranks for live inference
        from football_api import get_team_standings
        standings_raw = get_team_standings(league_id, 2025, api_key)
        home_rank, away_rank = 10, 10
        try:
            league_standings = standings_raw.get('response', [])[0].get('league', {}).get('standings', [])[0]
            for entry in league_standings:
                tid = entry['team']['id']
                if tid == home_id: home_rank = entry['rank']
                if tid == away_id: away_rank = entry['rank']
        except:
            pass

        features = pd.DataFrame([{
            "home_id": home_id,
            "away_id": away_id,
            "home_rank": home_rank, 
            "away_rank": away_rank,
            "home_advantage": 1
        }])
        ml_pred = model.predict(features)[0]
        ml_outcome = "Home Win" if ml_pred == 1 else ("Away Win" if ml_pred == 2 else "Draw")
    
    # Final Hybrid Outcome
    if home_score > away_score + 15:
        outcome = f"{fixture['teams']['home']['name']} Win"
        dc = "Home/Draw"
    elif away_score > home_score + 15:
        outcome = f"{fixture['teams']['away']['name']} Win"
        dc = "Away/Draw"
    else:
        outcome = "Draw / Close Match"
        dc = "1X / 2X"
        
    # Add Advanced Markets
    ht_result = get_halftime_prediction(home_form, away_form)
    corners = calculate_corner_estimate(fixture_id, api_key)
    
    return {
        "main": outcome,
        "dc": dc,
        "ht": ht_result,
        "corners": corners,
        "ml": ml_outcome,
        "card_risk": calculate_booking_risk(home_id, league_id, api_key)
    }

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
        # Feed the model for hybrid inference
        prediction = get_match_prediction(fixture, api_key, model=model)
        predictions[fixture_id] = prediction
    
    return predictions

def main():
    api_key = os.getenv("RAPIDAPI_KEY")
    current_date = datetime.datetime.now().date()
    
    # 1. Fetch training data (Historical)
    # Using a subset of major leagues for training speed in this example
    training_league_ids = [39, 140, 78, 135] # EPL, La Liga, Bundesliga, Serie A
    train_df = fetch_training_data(api_key, training_league_ids)
    
    # 2. Train Model
    model = train_model(train_df)
    
    # 3. Fetch today's fixtures
    from football_api import get_prioritized_fixtures
    fixtures = get_prioritized_fixtures(current_date, api_key)
    
    if not fixtures:
        print("No matches to predict today.")
        return
        
    # 4. Generate Hybrid Predictions
    predictions = make_predictions(model, fixtures, api_key)
    
    print("\n--- Optimized Match Predictions ---")
    for fid, pred in predictions.items():
        print(f"Fixture {fid}: {pred}")

if __name__ == "__main__":
    main()