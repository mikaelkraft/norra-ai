# test_api_fixtures.py
import os
import datetime
import requests
from dotenv import load_dotenv

print("Current Working Directory:", os.getcwd())
print("Does .env exist?", os.path.exists(".env"))

# Specify absolute path to .env
env_path = os.path.abspath(".env")
print("Absolute path to .env:", env_path)

load_dotenv(dotenv_path=env_path)

def diagnose():
    api_key = os.getenv("FOOTBALL_API_KEY")
    if not api_key:
        print("FOOTBALL_API_KEY not found in environment!")
        return

    # Check the current date on this system
    current_date = datetime.datetime.now().date()
    date_str = current_date.strftime("%Y-%m-%d")
    print(f"System Date: {date_str}")

    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"date": date_str}
    headers = {"x-apisports-key": api_key}

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        print(f"API Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get("response", [])
            print(f"Total fixtures returned by API: {len(fixtures)}")
            
            if fixtures:
                print("\nSample of returned fixtures:")
                for f in fixtures[:5]:
                    fixture_id = f['fixture']['id']
                    home = f['teams']['home']['name']
                    away = f['teams']['away']['name']
                    league_id = f['league']['id']
                    league_name = f['league']['name']
                    season = f['league']['season']
                    print(f"- ID: {fixture_id} | {home} vs {away} | League: {league_name} (ID: {league_id}, Season: {season})")
            else:
                print("API Errors/Warnings:", data.get("errors"), data.get("warnings"))
        else:
            print("API Response:", response.text)
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    diagnose()
