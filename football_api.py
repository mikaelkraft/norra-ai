#football_api.py
import random
from telnetlib import AUTHENTICATION
import requests
import datetime
import tweepy
import pandas as pd
import numpy as np

from Norra import post_predictions

def fetch_team_data(api_key, league_id):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams"
    querystring = {"league": league_id}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        team_data = response.json()
        return team_data
    else:
        print(f"Failed to fetch team data. Status code: {response.status_code}")
        return None

api_key = "008362339amsh83fe9d1584cd2e8p150ebejsnd291e823113c"
league_ids = [2, 3, 848, 39, 40, 78, 140, 135, 61, 94, 203, 399]  # List of league IDs

all_teams_data = {}

for league_id in league_ids:
    teams_data = fetch_team_data(api_key, league_id)
    if teams_data:
        all_teams_data[league_id] = teams_data
    else:
        print(f"Failed to fetch team data for League ID {league_id}")

def get_leagues(api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/leagues"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve leagues. Status code:", response.status_code)
        return None

def get_fixtures(league_id, season, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {
        "league": str(league_id),
        "season": str(season),
        "current": "true"
    }
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve fixtures. Status code:", response.status_code)
        return None


# Function to retrieve team statistics for a specific team in a league and season
def get_team_statistics(league_id, season, team_id, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams/statistics"

    querystring = {
        "league": str(league_id),
        "season": str(season),
        "team": str(team_id)
    }

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        print(response.text)  # Print the response content
        return response.json()  # Convert response to JSON
    else:
        print("Failed to retrieve team statistics. Status code:", response.status_code)
        return None  # Return None if the request fails

# Function to retrieve player statistics for a specific team in a league and season
def get_player_statistics(league_id, season, team_id, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/players"

    querystring = {
        "league": str(league_id),
        "season": str(season),
        "team": str(team_id)
    }

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        print(response.text)  # Print the response content
        return response.json()  # Convert response to JSON
    else:
        print("Failed to retrieve player statistics. Status code:", response.status_code)
        return None  # Return None if the request fails
    
    # Function to retrieve head-to-head statistics for specific teams in a league
def get_head_to_head_statistics(league_id, team_id1, team_id2, last_matches, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead"

    querystring = {
        "h2h": f"{team_id1}-{team_id2}",
        "league": str(league_id),
        "last": str(last_matches)
    }

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        print(response.text)  # Print the response content
        return response.json()  # Convert response to JSON
    else:
        print("Failed to retrieve head-to-head statistics. Status code:", response.status_code)
        return None  # Return None if the request fails

# Function to retrieve injuries for a specific team in a league and season
def get_team_injuries(league_id, season, team_id, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/injuries"

    querystring = {
        "league": str(league_id),
        "season": str(season),
        "team": str(team_id)
    }

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        print(response.text)  # Print the response content
        return response.json()  # Convert response to JSON
    else:
        print("Failed to retrieve team injuries. Status code:", response.status_code)
        return None  # Return None if the request fails

# Function to retrieve team standings in a league and season
def get_team_standings(league_id, season, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/standings"

    querystring = {
        "league": str(league_id),
        "season": str(season)
    }

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        print(response.text)  # Print the response content
        return response.json()  # Convert response to JSON
    else:
        print("Failed to retrieve team standings. Status code:", response.status_code)
        return None  # Return None if the request fails
    
def fetch_predictions(league_ids, api_key):
    predictions = {}

    for league_id in league_ids:
        # Fetch fixtures for the specific day leagues
        fixtures_data = get_fixtures(league_id, datetime.datetime.now().date())

        if fixtures_data:
            # Process fetched fixtures and generate predictions
            predictions[league_id] = generate_predictions(fixtures_data)  # Replace with your prediction logic
        else:
            print(f"Failed to fetch fixtures for League ID {league_id}.")

    return predictions

def generate_predictions(fixtures_data):
    predictions = {}

    for fixture in fixtures_data:
        home_team = fixture.get("teams", {}).get("home", {}).get("name", "Home")
        away_team = fixture.get("teams", {}).get("away", {}).get("name", "Away")

        # Replace this with your actual prediction logic
        # For simplicity, assume a random prediction (0 or 1)
        prediction = random.choice([0, 1])

        predictions[f"{home_team} vs {away_team}"] = prediction

    return predictions

def generate_predictions(fixtures_data):
    # Placeholder logic for generating predictions
    # Replace this with your actual prediction algorithm
    predictions = {}
    for match in fixtures_data:
        predictions[match["fixture"]["id"]] = "1X2 Prediction"
    return predictions

def post_predictions(predictions, api_key, consumer_key, consumer_secret, access_token, access_token_secret):
    # Authenticate with Tweepy API
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    # Check if authentication is successful
    if api.verify_credentials():
        print("Authentication with Twitter is successful.")
    else:
        print("Authentication with Twitter failed. Please check your credentials.")
        return

    # Post predictions to Twitter
    for match, prediction in predictions.items():
        # Adjust the format of 'match' and 'prediction' based on your data structure
        tweet = f"{match}: {prediction}"

        try:
            api.update_status(tweet)
            print(f"Prediction posted on Twitter: {tweet}")
        except tweepy.TweepError as e:
            print(f"Failed to post prediction on Twitter: {e}")

if __name__ == "__main__":
    # Example usage
    current_date = datetime.datetime.now().date()  # Replace with the actual date
    fetch_predictions(league_ids, current_date)