#football_api.py
import random
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

import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("RAPIDAPI_KEY")

# League Tiers
TIER_1_LEAGUES = [
    2,    # Champions League
    3,    # Europa League
    848,  # Conference League
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    88,   # Eredivisie
    94,   # Primeira Liga
    71,   # Brasileiro Série A
    203,  # Super Lig
    1,    # World Cup
    4,    # Euro Championship
    9,    # Copa America
    6     # AFCON
]

TIER_2_LEAGUES = [
    40,   # Championship
    141,  # Segunda Division
    136,  # Serie B
    79,   # Bundesliga 2
    62,   # Ligue 2
    399,  # Superliga (Denmark)
    253   # MLS
]

def get_prioritized_fixtures(date, api_key):
    """
    Fetches fixtures for the given date, prioritizing Tier 1 leagues.
    If no Tier 1 fixtures are found, it falls back to Tier 2.
    """
    print(f"Checking for Tier 1 matches on {date}...")
    all_fixtures = []
    
    # Try Tier 1
    for league_id in TIER_1_LEAGUES:
        # We use the current year as season, or date.year
        # Note: Some leagues cross years (2023-2024), season 2023.
        # For simplicity, we'll try to find fixtures for this date specifically.
        fixtures = get_fixtures(api_key, league_id=league_id, date=date)
        if fixtures:
            all_fixtures.extend(fixtures)
    
    if all_fixtures:
        print(f"Found {len(all_fixtures)} Tier 1 matches.")
        return all_fixtures

    print("No Tier 1 matches found. Checking Tier 2...")
    # Fallback to Tier 2
    for league_id in TIER_2_LEAGUES:
        fixtures = get_fixtures(api_key, league_id=league_id, date=date)
        if fixtures:
            all_fixtures.extend(fixtures)
            
    if all_fixtures:
        print(f"Found {len(all_fixtures)} Tier 2 matches.")
    else:
        print("No matches found in Tier 1 or Tier 2.")
        
    return all_fixtures

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

def get_fixtures(api_key, league_id=None, season=None, date=None, team_id=None, next_n=None):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {}
    if league_id: querystring["league"] = str(league_id)
    if season: querystring["season"] = str(season)
    if date: querystring["date"] = str(date)
    if team_id: querystring["team"] = str(team_id)
    if next_n: querystring["next"] = str(next_n)
    
    if not querystring and not next_n:
        querystring["current"] = "true"

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve fixtures. Status code: {response.status_code}")
        return []


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
    """
    Placeholder logic for generating predictions.
    This will be replaced by the more advanced logic in prediction_model.py.
    """
    predictions = {}
    for match in fixtures_data:
        fixture_id = match.get("fixture", {}).get("id")
        home = match.get("teams", {}).get("home", {}).get("name")
        away = match.get("teams", {}).get("away", {}).get("name")
        predictions[fixture_id] = f"{home} vs {away}: 1X2 Prediction"
    return predictions

# Function to retrieve lineups for a specific fixture
def get_lineups(fixture_id, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/lineups"
    querystring = {"fixture": str(fixture_id)}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve lineups. Status code: {response.status_code}")
        return []

# Function to retrieve predictions for a specific fixture
def get_predictions(fixture_id, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/predictions"
    querystring = {"fixture": str(fixture_id)}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve predictions. Status code: {response.status_code}")
        return []

if __name__ == "__main__":
    # Example usage
    current_date = datetime.datetime.now().date()  # Replace with the actual date
    fetch_predictions(league_ids, current_date)