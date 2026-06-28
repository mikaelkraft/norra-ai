# espn_api.py  
import requests
import datetime

# Map ESPN league abbreviations to API-Football league IDs
LEAGUE_MAPPING = {
    "uefa.champions": 2,
    "uefa.europa": 3,
    "eng.1": 39,
    "esp.1": 140,
    "ita.1": 135,
    "ger.1": 78,
    "fra.1": 61,
    "ned.1": 88,
    "por.1": 94,
    "bra.1": 71,
    "tur.1": 203,
    "usa.1": 253,
    "ksa.1": 307,
    "arg.1": 128,
    "mex.1": 262,
    "sco.1": 179,
    "swe.1": 113,
    "nor.1": 103,
    "jpn.1": 98,
    "eng.2": 40,
    "esp.2": 141,
    "ita.2": 136,
    "ger.2": 79,
    "fra.2": 62,
    "bel.1": 144,
    "aut.1": 218,
    "sui.1": 207,
    "den.1": 119,
    "aus.1": 188,
    "chn.1": 169,
    "fin.1": 244,
    "usa.w.1": 258,
    "eng.w.1": 44,
    "fifa.world": 1,
    "uefa.euro": 4,
    "conmebol.america": 9,
    "caf.nations": 6,
    "fifa.world.q.uefa": 10,
    "fifa.world.q.conmebol": 11,
    "fifa.world.q.concacaf": 12,
    "fifa.world.q.caf": 13,
    "fifa.world.q.afc": 14,
    "fifa.world.q.ofc": 15,
    "fifa.world.q.playoffs": 16
}

def fetch_espn_today_fixtures():
    """
    Fetches soccer matches for today across major ESPN leagues matching our Tier 1 and Tier 2 lists.
    No API keys required.
    """
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    fixtures = []
    
    print(f"Fetching free schedule from ESPN Scoreboard for date: {date_str}...")
    
    for espn_code, api_football_id in LEAGUE_MAPPING.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_code}/scoreboard?dates={date_str}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                events = res.json().get("events", [])
                for event in events:
                    competition = event.get('competitions', [{}])[0]
                    competitors = competition.get('competitors', [])
                    if len(competitors) < 2:
                        continue
                    
                    # ESPN lists Home team typically at index 0 or checks home/away flag
                    home_team = next((c['team']['displayName'] for c in competitors if c.get('homeAway') == 'home'), competitors[0]['team']['displayName'])
                    away_team = next((c['team']['displayName'] for c in competitors if c.get('homeAway') == 'away'), competitors[1]['team']['displayName'])
                    
                    fixtures.append({
                        "home": home_team,
                        "away": away_team,
                        "espn_league": espn_code,
                        "league_id": api_football_id,
                        "date": event.get('date'),
                        "status": event.get('status', {}).get('type', {}).get('description', 'Scheduled'),
                        "name": f"{home_team} vs {away_team}"
                    })
        except Exception as e:
            # Silently catch so one league failing doesn't block the rest
            pass
            
    print(f"ESPN Scoreboard: Found {len(fixtures)} matches matching prioritized tiers today.")
    return fixtures

def fetch_sportsdb_today_fixtures():
    """
    Fallback schedule provider: Fetches today's soccer matches from TheSportsDB free developer API.
    Does not require a custom API key.
    """
    import datetime
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={date_str}&s=Soccer"
    fixtures = []
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            events = res.json().get("events", [])
            if events:
                for event in events:
                    home = event.get("strHomeTeam")
                    away = event.get("strAwayTeam")
                    league_name = event.get("strLeague")
                    
                    # Convert TheSportsDB league name to API-Football league ID
                    league_id = None
                    l_lower = league_name.lower() if league_name else ""
                    if "premier league" in l_lower and "english" in l_lower: league_id = 39
                    elif "la liga" in l_lower: league_id = 140
                    elif "serie a" in l_lower and "ital" in l_lower: league_id = 135
                    elif "bundesliga" in l_lower and "german" in l_lower: league_id = 78
                    elif "ligue 1" in l_lower and "french" in l_lower: league_id = 61
                    elif "mls" in l_lower or "major league soccer" in l_lower: league_id = 253
                    
                    if league_id and home and away:
                        fixtures.append({
                            "home": home,
                            "away": away,
                            "espn_league": "sportsdb",
                            "league_id": league_id,
                            "date": event.get("dateEvent"),
                            "status": event.get("strStatus", "Scheduled"),
                            "name": f"{home} vs {away}"
                        })
    except Exception as e:
        print(f"TheSportsDB fetch failed: {e}")
        
    return fixtures

def fetch_combined_today_fixtures():
    """Combines ESPN scoreboard and TheSportsDB schedule fixtures, removing duplicates."""
    espn_fixtures = fetch_espn_today_fixtures()
    sportsdb_fixtures = fetch_sportsdb_today_fixtures()
    
    combined = list(espn_fixtures)
    existing_pairs = set()
    for f in espn_fixtures:
        h = f["home"].lower().strip()
        a = f["away"].lower().strip()
        existing_pairs.add(tuple(sorted([h, a])))
        
    for f in sportsdb_fixtures:
        h = f["home"].lower().strip()
        a = f["away"].lower().strip()
        signature = tuple(sorted([h, a]))
        if signature not in existing_pairs:
            combined.append(f)
            existing_pairs.add(signature)
            
    print(f"Combined Schedule Caches: Found {len(combined)} total matches globally today.")
    return combined
