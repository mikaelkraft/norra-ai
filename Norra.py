import numpy as np
import tweepy
from football_api import get_fixtures
import datetime


# X API credentials
consumer_key = "0m7Ql5WM2MwhmAsTWs5ONOHr9"
consumer_secret = "7mWbYgmg0jgOQei62HlI3HXnbKlIo7QBjwKTsrgaCH91aMVLAu"
access_token = "1703978900202590208-ANVmJCTdqKToSZTKP99b6Q6Zfg5w1y"
access_token_secret = "E6DMfalt3NWNL6D1tGxe1LOTwNNy8bbVK4PueDOoRcoQu"

# Authenticate with X
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# Check if authentication is successful by printing a message
if api.verify_credentials():
    print("Authentication is successful. Norra is ready to use X! (formerly Twitter)")
else:
    print("Authentication failed. Please check your credentials.")


     # API_football Actual API credentials and league ID
api_key = "008362339amsh83fe9d1584cd2e8p150ebejsnd291e823113c"
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

    fixtures_data = get_fixtures(league_id, season, start_date, end_date, api_key)

    if fixtures_data:
        # Simplify the output to avoid potential encoding issues
        print(f"Fetched historical data for League ID {league_id}.")
    else:
        print(f"Failed to fetch historical data for League ID {league_id}.")

def fetch_predictions(api_key):
    current_date = datetime.datetime.now().date()

    # Leagues for different days
    leagues_mapping = {
        0: [39, 78, 140, 135, 61, 203, 399, 40, 79],  # Monday
        1: [2],           # Tuesday
        2: [2],           # Wednesday
        3: [3, 848],      # Thursday
        4: [39, 78, 140, 135, 61, 203, 399, 40, 79],  # Friday
        5: [39, 78, 140, 135, 61, 203, 399, 40, 79],  # Saturday
        6: [39, 78, 140, 135, 61, 203, 399, 40, 79]   # Sunday
    }

    # Get the list of leagues for the current day
    today_leagues = leagues_mapping[current_date.weekday()]

    # Fetch fixtures for the specific day leagues
    fixtures_data = {}
    for league_id in today_leagues:
        fixtures_data[league_id] = get_fixtures(league_id, current_date, api_key)

    # Check if there are no matches for the specified leagues
    if not any(fixtures_data.values()):
        print("No matches found for the specified leagues on this day.")
        return

    # Process fetched fixtures and generate predictions
    predictions = generate_predictions(fixtures_data)  # Replace with your prediction logic
    # Post predictions to Twitter
    post_predictions(predictions, api_key, consumer_key, consumer_secret, access_token, access_token_secret)

def generate_predictions(fixtures_data):
    predictions = {}

    for league_id, fixtures in fixtures_data.items():
        for fixture in fixtures:
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            home_goals = np.random.randint(0, 4)  # Simple random prediction for home team goals (0 to 3)
            away_goals = np.random.randint(0, 4)  # Simple random prediction for away team goals (0 to 3)

            result = f"{home_team} vs {away_team}: {home_goals} - {away_goals}"
            predictions[result] = {"home_goals": home_goals, "away_goals": away_goals}

    return predictions
def post_predictions(predictions):
    # Authenticate with Twitter API
    auth = tweepy.OAuthHandler("0m7Ql5WM2MwhmAsTWs5ONOHr9", "7mWbYgmg0jgOQei62HlI3HXnbKlIo7QBjwKTsrgaCH91aMVLAu")
    auth.set_access_token("1703978900202590208-ANVmJCTdqKToSZTKP99b6Q6Zfg5w1y", "E6DMfalt3NWNL6D1tGxe1LOTwNNy8bbVK4PueDOoRcoQu")
    api = tweepy.API(auth)

    if api.verify_credentials():
        print("Authentication with Twitter is successful. Posting predictions.")
    else:
        print("Authentication with Twitter failed. Please check your credentials.")
        return

    # Post predictions on Twitter
    for match, prediction in predictions.items():
        home_team, away_team = match.split(" vs ")
        home_goals, away_goals = prediction["home_goals"], prediction["away_goals"]

        tweet_text = f"{home_team} vs {away_team}: {home_goals} - {away_goals}"
        
        try:
            api.update_status(tweet_text)
            print(f"Prediction posted on Twitter: {tweet_text}")
        except tweepy.TweepError as e:
            print(f"Failed to post prediction on Twitter. Error: {e}")

if __name__ == "__main__":
    fetch_predictions()