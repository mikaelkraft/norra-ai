#football_api.py
import random
import requests
import datetime
import tweepy
import pandas as pd
import numpy as np

# Global quota safeguard
API_QUOTA_EXCEEDED = False

class ResponseWrapper:
    def __init__(self, response):
        self._response = response
        
    @property
    def status_code(self):
        return self._response.status_code
        
    @property
    def text(self):
        # Truncate text representation in logs to prevent "output too large" cron failure
        t = self._response.text
        if len(t) > 200:
            return t[:200] + "... [TRUNCATED to prevent cron output limit failure]"
        return t
        
    def json(self):
        return self._response.json()
        
    def __getattr__(self, name):
        return getattr(self._response, name)

_original_get = requests.get

def requests_get_wrapper(url, *args, **kwargs):
    global API_QUOTA_EXCEEDED
    if API_QUOTA_EXCEEDED:
        # Return a mock response indicating quota limit exceeded
        class MockResponse:
            status_code = 429
            text = '{"errors": {"token": "Quota limit exceeded (safeguard)"}}'
            def json(self):
                return {"errors": {"token": "Quota limit exceeded (safeguard)"}, "response": []}
        return MockResponse()
        
    try:
        response = _original_get(url, *args, **kwargs)
        if response.status_code == 429:
            print("API response: 429 Too Many Requests. API quota exceeded.")
            API_QUOTA_EXCEEDED = True
            
        elif response.status_code == 200:
            try:
                data = response.json()
                errors = data.get("errors")
                if errors:
                    error_msgs = str(errors).lower()
                    if "limit" in error_msgs or "quota" in error_msgs or "request limit" in error_msgs:
                        print(f"API returned limit error: {errors}. Setting API_QUOTA_EXCEEDED flag.")
                        API_QUOTA_EXCEEDED = True
            except:
                pass
        return ResponseWrapper(response)
    except Exception as e:
        print(f"Exception during API request to {url}: {e}")
        class MockErrorResponse:
            status_code = 500
            text = str(e)
            def json(self):
                return {"errors": {"exception": str(e)}, "response": []}
        return MockErrorResponse()

requests.get = requests_get_wrapper



def fetch_team_data(api_key, league_id):
    url = "https://v3.football.api-sports.io/teams"
    querystring = {"league": league_id}
    headers = {
        "x-apisports-key": api_key
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

api_key = os.getenv("FOOTBALL_API_KEY")

# League Tiers (Expanded for 365-day coverage & summer/women leagues)
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
    6,    # AFCON
    10,   # WC Qualification Europe
    11,   # WC Qualification South America
    12,   # WC Qualification North & Central America
    13,   # WC Qualification Africa
    14,   # WC Qualification Asia
    15,   # WC Qualification Oceania
    16,   # WC Qualification Intercontinental Play-offs
    113,  # Allsvenskan (Sweden)
    103,  # Eliteserien (Norway)
    98    # J1 League (Japan)
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
    119,  # Superliga (Denmark)
    188,  # A-League (Australia)
    305,  # Qatar Stars League
    235,  # Russian Premier League
    41,   # League One
    202,  # Vietnamese V.League 1
    399,  # Superliga (Denmark alternate)
    169,  # China Super League
    244,  # Veikkausliiga (Finland)
    358,  # Urvalsdeild (Iceland)
    115,  # Damallsvenskan Women (Sweden)
    258,  # NWSL Women (USA)
    74,   # Brasileiro Feminino A1 (Brazil)
    44    # WSL Women (England)
]

def get_prioritized_fixtures(date, api_key):
    """
    Optimized: Fetches ALL fixtures for the given date in one call,
    then filters them locally by Tier 1 and Tier 2 lists.
    """
    date_str = date.strftime("%Y-%m-%d")
    print(f"Fetching global fixtures for {date_str}...")
    
    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"date": date_str}
    headers = {
        "x-apisports-key": api_key
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
            
        print("No matches found in Tier 1 or Tier 2 today. Activating off-season universal fallback...")
        # Filter out youth matches, lower reserves, or simulated leagues to keep predictions high-quality
        excluded_keywords = ["youth", "u19", "u21", "u23", "u17", "u20", "reserve", "simulated", "virtual"]
        tier_3_candidates = []
        for f in all_data:
            league_name = f.get('league', {}).get('name', '').lower()
            if any(kw in league_name for kw in excluded_keywords):
                continue
            tier_3_candidates.append(f)
            
        if tier_3_candidates:
            selected_candidates = tier_3_candidates[:8]
            print(f"Found {len(tier_3_candidates)} candidates. Selecting top {len(selected_candidates)} for fallback analysis.")
            return selected_candidates
            
        print("No matches found globally today.")
        return []
    except Exception as e:
        print(f"Error in prioritized fixture discovery: {e}")
        return []

def get_leagues(api_key):
    url = "https://v3.football.api-sports.io/leagues"
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to retrieve leagues. Status code:", response.status_code)
        return None

def get_fixtures(api_key, league_id=None, season=None, date=None, team_id=None, next_n=None, last_n=None):
    url = "https://v3.football.api-sports.io/fixtures"
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
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve fixtures. Status code: {response.status_code}")
        return []


# Function to retrieve team statistics for a specific team in a league and season
def get_team_statistics(league_id, season, team_id, api_key):
    url = "https://v3.football.api-sports.io/teams/statistics"

    querystring = {
        "league": str(league_id),
        "season": str(season),
        "team": str(team_id)
    }

    headers = {
        "x-apisports-key": api_key
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
    url = "https://v3.football.api-sports.io/players"

    querystring = {
        "league": str(league_id),
        "season": str(season),
        "team": str(team_id)
    }

    headers = {
        "x-apisports-key": api_key
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
    url = "https://v3.football.api-sports.io/fixtures/headtohead"

    querystring = {
        "h2h": f"{team_id1}-{team_id2}",
        "league": str(league_id),
        "last": str(last_matches)
    }

    headers = {
        "x-apisports-key": api_key
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
    url = "https://v3.football.api-sports.io/injuries"

    querystring = {
        "league": str(league_id),
        "season": str(season),
        "team": str(team_id)
    }

    headers = {
        "x-apisports-key": api_key
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
    url = "https://v3.football.api-sports.io/standings"

    querystring = {
        "league": str(league_id),
        "season": str(season)
    }

    headers = {
        "x-apisports-key": api_key
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
    url = "https://v3.football.api-sports.io/fixtures/lineups"
    querystring = {"fixture": fixture_id}
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve lineups. Status code: {response.status_code}")
        return []

# Function to retrieve statistics for a specific fixture
def get_fixture_statistics(fixture_id, api_key):
    url = "https://v3.football.api-sports.io/fixtures/statistics"
    querystring = {"fixture": fixture_id}
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve statistics. Status code: {response.status_code}")
        return []

# Function to retrieve a single fixture by ID (to check results)
def get_fixture_by_id(fixture_id, api_key):
    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"id": fixture_id}
    headers = {
        "x-apisports-key": api_key
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
    url = "https://v3.football.api-sports.io/predictions"
    querystring = {"fixture": fixture_id}
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve predictions. Status code: {response.status_code}")
        return []

# Function to retrieve odds for a specific fixture
def get_odds(fixture_id, api_key):
    url = "https://v3.football.api-sports.io/odds"
    querystring = {"fixture": fixture_id}
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve odds. Status code: {response.status_code}")
        return []

# Function to retrieve all fixtures for a specific date
def get_fixtures_by_date(date_str, api_key):
    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"date": date_str}
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve fixtures for date {date_str}. Status code: {response.status_code}")
        return []

# Function to retrieve top scorers for a league/season
def get_top_scorers(league_id, season, api_key):
    url = "https://v3.football.api-sports.io/players/topscorers"
    querystring = {"league": league_id, "season": season}
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve top scorers. Status code: {response.status_code}")
        return []

# Function to retrieve Extended H2H (Multi-Season)
def get_extended_h2h(home_id, away_id, api_key, last_n=10):
    url = "https://v3.football.api-sports.io/fixtures/headtohead"
    querystring = {"h2h": f"{home_id}-{away_id}", "last": last_n}
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve extended H2H. Status code: {response.status_code}")
        return []

# Function to retrieve Coach/Manager history for a team
def get_coach_history(team_id, api_key):
    url = "https://v3.football.api-sports.io/coachs"
    querystring = {"team": team_id}
    headers = {
        "x-apisports-key": api_key
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Failed to retrieve coach history. Status code: {response.status_code}")
        return []

if __name__ == "__main__":
    # Example usage: fetch prioritized fixtures for today
    current_date = datetime.datetime.now().date()
    if api_key:
        fixtures = get_prioritized_fixtures(current_date, api_key)
        print(f"Found {len(fixtures)} prioritized fixtures for today.")
    else:
        print("FOOTBALL_API_KEY not configured in environment. Example run skipped.")