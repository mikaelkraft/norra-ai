#football_api.py
import random
import requests
import datetime
import tweepy
import pandas as pd
import numpy as np



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

# League Tiers (Expanded for 365-day coverage)
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
    253,  # MLS
    307,  # Saudi Pro League
    128,  # Argentina Liga Profesional
    262,  # Liga MX
    179,  # Scotland Premiership
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
    144,  # Jupiler Pro League (Belgium)
    218,  # Austrian Bundesliga
    207,  # Swiss Super League
    113,  # Allsvenskan (Sweden)
    119,  # Superliga (Denmark)
    103,  # Eliteserien (Norway)
    188,  # A-League (Australia)
    98,   # J1 League (Japan)
    305,  # Qatar Stars League
    235,  # Russian Premier League
    41,   # League One
    202,  # Vietnamese V.League 1
    399   # Superliga (Denmark alternate)
]

def get_prioritized_fixtures(date, api_key):
    """
    Optimized: Fetches ALL fixtures for the given date in one call,
    then filters them locally by Tier 1 and Tier 2 lists.
    """
    date_str = date.strftime("%Y-%m-%d")
    print(f"Fetching global fixtures for {date_str}...")
    
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {"date": date_str}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200:
            print(f"Failed to fetch global fixtures. Status: {response.status_code}")
            return []
        
        all_data = response.json().get("response", [])
        print(f"Found {len(all_data)} total matches globally today.")
        
        # Filter Tier 1
        tier_1_found = [f for f in all_data if f['league']['id'] in TIER_1_LEAGUES]
        
        if tier_1_found:
            print(f"Found {len(tier_1_found)} matches in Tier 1 leagues.")
            return tier_1_found
        
        # Fallback to Tier 2
        print("No Tier 1 matches. Checking Tier 2...")
        tier_2_found = [f for f in all_data if f['league']['id'] in TIER_2_LEAGUES]
        
        if tier_2_found:
            print(f"Found {len(tier_2_found)} matches in Tier 2 leagues.")
            return tier_2_found
            
        print("No matches found in Tier 1 or Tier 2 today.")
        return []
    except Exception as e:
        print(f"Error in prioritized fixture discovery: {e}")
        return []

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

def get_fixtures(api_key, league_id=None, season=None, date=None, team_id=None, next_n=None, last_n=None):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {}
    if league_id: querystring["league"] = str(league_id)
    if season: querystring["season"] = str(season)
    if date: querystring["date"] = str(date)
    if team_id: querystring["team"] = str(team_id)
    if next_n: querystring["next"] = str(next_n)
    if last_n: querystring["last"] = str(last_n)
    
    if not querystring and not next_n and not last_n:
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

# Function to retrieve statistics for a specific fixture
def get_fixture_statistics(fixture_id, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/statistics"
    querystring = {"fixture": str(fixture_id)}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve statistics. Status code: {response.status_code}")
        return []

# Function to retrieve a single fixture by ID (to check results)
def get_fixture_by_id(fixture_id, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {"id": str(fixture_id)}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        data = response.json().get("response", [])
        return data[0] if data else None
    else:
        print(f"Failed to retrieve fixture by ID. Status code: {response.status_code}")
        return None

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

# Function to retrieve odds for a specific fixture
def get_odds(fixture_id, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/odds"
    querystring = {"fixture": str(fixture_id)}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve odds. Status code: {response.status_code}")
        return []

# Function to retrieve all fixtures for a specific date
def get_fixtures_by_date(date_str, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {"date": date_str}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve fixtures for date {date_str}. Status code: {response.status_code}")
        return []

# Function to retrieve top scorers for a league/season
def get_top_scorers(league_id, season, api_key):
    url = "https://api-football-v1.p.rapidapi.com/v3/players/topscorers"
    querystring = {"league": str(league_id), "season": str(season)}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve top scorers. Status code: {response.status_code}")
        return []

# Function to retrieve Extended H2H (Multi-Season)
def get_extended_h2h(home_id, away_id, api_key, last_n=10):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead"
    querystring = {"h2h": f"{home_id}-{away_id}", "last": str(last_n)}
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve extended H2H. Status code: {response.status_code}")
        return []

if __name__ == "__main__":
    # Example usage
    current_date = datetime.datetime.now().date()  # Replace with the actual date
    fetch_predictions(league_ids, current_date)