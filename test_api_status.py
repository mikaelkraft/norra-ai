# test_api_status.py
import os
import ssl
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()

def check_status():
    api_key = os.getenv("FOOTBALL_API_KEY")
    if not api_key:
        print("FOOTBALL_API_KEY not found in environment!")
        return

    # Disable SSL verification for local diagnostic purposes
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print("Checking API-Football Status and Plan...")
    req = urllib.request.Request(
        "https://v3.football.api-sports.io/status",
        headers={"x-apisports-key": api_key, "User-Agent": "Mozilla/5.0"}
    )
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            print("Status Response:")
            print(json.dumps(res_data, indent=2))
    except Exception as e:
        print(f"Failed to check API status: {e}")

    # Check today's fixtures
    import datetime
    current_date = datetime.datetime.now().date()
    date_str = current_date.strftime("%Y-%m-%d")
    print(f"\nFetching fixtures for date: {date_str}...")
    
    fixtures_url = f"https://v3.football.api-sports.io/fixtures?date={date_str}"
    req_fixtures = urllib.request.Request(
        fixtures_url,
        headers={"x-apisports-key": api_key, "User-Agent": "Mozilla/5.0"}
    )
    
    try:
        with urllib.request.urlopen(req_fixtures, context=ctx, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            fixtures = res_data.get("response", [])
            print(f"Total fixtures returned: {len(fixtures)}")
            
            # Print errors/warnings if any
            errors = res_data.get("errors")
            warnings = res_data.get("warnings")
            if errors: print("API Errors:", errors)
            if warnings: print("API Warnings:", warnings)
            
            if fixtures:
                print("\nActive leagues today:")
                leagues = {}
                for f in fixtures:
                    lid = f['league']['id']
                    lname = f['league']['name']
                    leagues[lid] = lname
                for lid, lname in list(leagues.items())[:15]:
                    print(f"- ID: {lid} | {lname}")
            else:
                print("No fixtures returned.")
    except Exception as e:
        print(f"Failed to check fixtures: {e}")

if __name__ == "__main__":
    check_status()
