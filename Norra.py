import datetime
import random
import os
from dotenv import load_dotenv
import numpy as np
import tweepy

# X API credentials
consumer_key = os.getenv("X_CONSUMER_KEY")
consumer_secret = os.getenv("X_CONSUMER_SECRET")
access_token = os.getenv("X_ACCESS_TOKEN")
access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

# Authenticate with X
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# Check if authentication is successful by printing a message
try:
    if api.verify_credentials():
        print("Authentication is successful. Norra is ready to use X! (formerly Twitter)")
    else:
        print("Authentication failed. Please check your credentials.")
except Exception as e:
    print(f"Authentication failed: {e}")


# API_football Actual API credentials and league ID
api_key = os.getenv("RAPIDAPI_KEY")
# List of leagues with their IDs from the provided table
leagues = [
    {"league_id": 2, "season": 2023, "start_date": "2023-06-27", "end_date": "2023-12-13"},
    {"league_id": 39, "season": 2023, "start_date": "2023-10-28", "end_date": "2023-11-05"},
    {"league_id": 40, "season": 2023, "start_date": "2023-08-04", "end_date": "2024-05-04"},
    {"league_id": 78, "season": 2023, "start_date": "2023-08-18", "end_date": "2024-05-18"},
    {"league_id": 79, "season": 2023, "start_date": "2023-07-28", "end_date": "2024-05-19"},
    {"league_id": 140, "season": 2023, "start_date": "2023-08-11", "end_date": "2024-05-26"},
    {"league_id": 135, "season": 2023, "start_date": "2023-08-19", "end_date": "2024-05-26"},
    {"league_id": 61, "season": 2023, "start_date": "2023-08-13", "end_date": "2024-05-18"},
    {"league_id": 94, "season": 2023, "start_date": "2023-08-13", "end_date": "2024-05-19"},
    {"league_id": 203, "season": 2023, "start_date": "2023-08-13", "end_date": "2024-05-19"},
    {"league_id": 399, "season": 2024, "start_date": "2023-09-17", "end_date": "2024-06-09"}
    
]


for league in leagues:
    league_id = league["league_id"]
    season = league["season"]
    start_date = league["start_date"]
    end_date = league["end_date"]

    fixtures_data = get_fixtures(api_key, league_id=league_id, season=season)

    if fixtures_data:
        # Simplify the output to avoid potential encoding issues
        print(f"Fetched historical data for League ID {league_id}.")
    else:
        print(f"Failed to fetch historical data for League ID {league_id}.")

def fetch_predictions(api_key=None):
    if api_key is None:
        api_key = os.getenv("RAPIDAPI_KEY")
    current_date = datetime.datetime.now().date()

    # Fetch prioritized fixtures for today
    from football_api import get_prioritized_fixtures
    fixtures = get_prioritized_fixtures(current_date, api_key)

    if not fixtures:
        print(f"No matches found for Tier 1 or Tier 2 leagues on {current_date}.")
        return

    # Process fetched fixtures and generate predictions
    predictions = generate_predictions(fixtures, api_key)
    
    # Post predictions to X
    post_predictions(predictions)

def generate_predictions(fixtures, api_key):
    """
    Richer prediction generation using lineups, injuries, and form.
    """
    from football_api import get_predictions, get_lineups
    predictions = {}

    for fixture in fixtures:
        fixture_id = fixture['fixture']['id']
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        
        # Get native API predictions/advice
        api_preds = get_predictions(fixture_id, api_key)
        advice = "No specific advice"
        winner = "Unknown"
        conf = "50%"
        
        if api_preds:
            p = api_preds[0]
            advice = p.get('predictions', {}).get('advice', advice)
            winner = p.get('predictions', {}).get('winner', {}).get('name', winner)
            win_odds = p.get('predictions', {}).get('percent', {})
            # Pick the highest % for confidence
            # { "home": "45%", "draw": "25%", "away": "30%" }
            mapping = {"home": home_team, "away": away_team, "draw": "Draw"}
            winner_key = p.get('predictions', {}).get('winner', {}).get('comment', 'home').lower()
            if 'home' in winner_key: winner = home_team
            elif 'away' in winner_key: winner = away_team
            
            conf = win_odds.get(winner_key if winner_key in win_odds else 'home', '50%')

        result_key = f"{home_team} vs {away_team}"
        predictions[result_key] = {
            "winner": winner,
            "confidence": conf,
            "advice": advice,
            "home": home_team,
            "away": away_team
        }

    return predictions
def post_predictions(predictions):
    # Authenticate with X API
    consumer_key = os.getenv("X_CONSUMER_KEY")
    consumer_secret = os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    if api.verify_credentials():
        print("Authentication with Twitter is successful. Posting predictions.")
    else:
        print("Authentication with Twitter failed. Please check your credentials.")
        return

    # Post predictions on X
    for match, data in predictions.items():
        home = data['home']
        away = data['away']
        winner = data['winner']
        conf = data['confidence']
        advice = data['advice']

        tweet_text = (
            f"🏆 Match: {home} vs {away}\n"
            f"🔮 Prediction: {winner} to win ({conf})\n"
            f"💡 Advice: {advice}\n\n"
            f"#NorraAI #FootballPredictions #API_Football"
        )
        
        try:
            api.update_status(tweet_text)
            print(f"Prediction posted: {match}")
        except Exception as e:
            print(f"Failed to post prediction for {match}: {e}")

if __name__ == "__main__":
    fetch_predictions()