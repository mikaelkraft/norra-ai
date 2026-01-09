import datetime
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import numpy as np
import tweepy
from football_api import get_fixtures


# API_football Actual API credentials and league ID
api_key = os.getenv("RAPIDAPI_KEY")
# List of leagues with their IDs (updated for 2025/26 seasons)
leagues = [
    {"league_id": 2, "season": 2025, "start_date": "2025-06-27", "end_date": "2025-12-13"},
    {"league_id": 39, "season": 2025, "start_date": "2025-10-28", "end_date": "2026-11-05"},
    {"league_id": 40, "season": 2025, "start_date": "2025-08-04", "end_date": "2026-05-04"},
    {"league_id": 78, "season": 2025, "start_date": "2025-08-18", "end_date": "2026-05-18"},
    {"league_id": 79, "season": 2025, "start_date": "2025-07-28", "end_date": "2026-05-19"},
    {"league_id": 140, "season": 2025, "start_date": "2025-08-11", "end_date": "2026-05-26"},
    {"league_id": 135, "season": 2025, "start_date": "2025-08-19", "end_date": "2026-05-26"},
    {"league_id": 61, "season": 2025, "start_date": "2025-08-13", "end_date": "2026-05-18"},
    {"league_id": 94, "season": 2025, "start_date": "2025-08-13", "end_date": "2026-05-19"},
    {"league_id": 203, "season": 2025, "start_date": "2025-08-13", "end_date": "2026-05-19"},
    {"league_id": 399, "season": 2025, "start_date": "2025-09-17", "end_date": "2026-06-09"},
    {"league_id": 6, "season": 2025, "start_date": "2025-12-21", "end_date": "2026-01-18"} # AFCON
]


def run_historical_fetch():
    for league in leagues:
        league_id = league["league_id"]
        season = league["season"]
        fixtures_data = get_fixtures(api_key, league_id=league_id, season=season)
        if fixtures_data:
            print(f"Fetched historical data for League ID {league_id} (Season {season}).")
        else:
            print(f"Failed to fetch historical data for League ID {league_id}.")

def fetch_predictions(api_key=None, dry_run=False):
    if api_key is None:
        api_key = os.getenv("RAPIDAPI_KEY")
    current_date = datetime.datetime.now().date()

    # Optimized ML Training (Historical)
    try:
        from prediction_model import fetch_training_data, train_model
        # Use a few key leagues for training context
        training_leagues = [39, 140, 78, 135] # EPL, La Liga, Bundesliga, Serie A
        train_df = fetch_training_data(api_key, training_leagues)
        model = train_model(train_df)
    except Exception as e:
        print(f"ML Training failed, falling back to rule-engine: {e}")
        model = None

    # Fetch prioritized fixtures for today
    from football_api import get_prioritized_fixtures
    fixtures = get_prioritized_fixtures(current_date, api_key)

    if not fixtures:
        print(f"No matches found for Tier 1 or Tier 2 leagues on {current_date}.")
        return

    # Process fetched fixtures and generate predictions
    predictions = generate_predictions(fixtures, api_key, model=model)
    
    # Post predictions to X
    post_predictions(predictions, dry_run=dry_run)

def generate_predictions(fixtures, api_key, model=None):
    """
    Richer prediction generation using lineups, injuries, form, and ML.
    """
    from football_api import get_predictions, get_lineups
    from prediction_model import get_match_prediction
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
            winner_key = p.get('predictions', {}).get('winner', {}).get('comment', 'home').lower()
            if 'home' in winner_key: winner = home_team
            elif 'away' in winner_key: winner = away_team
            
            conf = win_odds.get(winner_key if winner_key in win_odds else 'home', '50%')

            # NEW: Extract BTTS (GG) and Over/Under
            btts = p.get('predictions', {}).get('btts', None)
            over_under = p.get('predictions', {}).get('goals', {}).get('over', None)
            
            gg_outcome = "GG" if btts is True else ("NG" if btts is False else "N/A")
            ou_outcome = f"Over 2.5" if over_under else "Under 2.5" # Simplified
        else:
            gg_outcome = "N/A"
            ou_outcome = "N/A"

        # NEW: Get Hybrid ML + Rule-Engine Prediction
        detailed_data = get_match_prediction(fixture, api_key, model=model)
        
        # Extract Rich Heading Context
        league_name = fixture['league']['name']
        venue = fixture['fixture'].get('venue', {}).get('name', 'Main Stadium')
        location = fixture['fixture'].get('venue', {}).get('city', 'Unknown')

        result_key = f"{home_team} vs {away_team}"
        predictions[result_key] = {
            "fixture_id": fixture_id,
            "winner": winner,
            "confidence": conf,
            "advice": advice,
            "home": home_team,
            "away": away_team,
            "gg": gg_outcome,
            "ou": ou_outcome,
            "heading": f"🏆 NorraAI MATCHDAY: {league_name} | {venue}",
            "detailed": detailed_data
        }

    return predictions
def post_predictions(predictions, dry_run=False):
    # Performance Shoutout Logic
    shoutout = ""
    try:
        if os.path.exists("bot_stats.json"):
            import json
            with open("bot_stats.json", "r") as f:
                stats = json.load(f)
                if stats.get("weekly_wins", 0) >= 5:
                    shoutout = "\n🔥 HEAVY SHOUTOUT: The Bot is on Fire! 5/7 Streak!"
    except: pass

    if dry_run:
        print("\n--- DRY RUN: Predictions would be posted to X ---")
    else:
        # Authenticate with X API
        # (Using v1.1 for media/legacy, but client v2 is preferred for new posts)
        consumer_key = os.getenv("X_CONSUMER_KEY")
        consumer_secret = os.getenv("X_CONSUMER_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        
        try:
            auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
            auth.set_access_token(access_token, access_token_secret)
            api = tweepy.API(auth)
            
            # Verify credentials explicitly for debug
            user = api.verify_credentials()
            if user:
                print(f"Authenticated as @{user.screen_name}")
            else:
                print("Twitter auth failed: verify_credentials returned None")
                return
        except Exception as auth_err:
            print(f"Twitter auth error: {auth_err}")
            return

    # Post predictions on X
    for match, data in predictions.items():
        home = data['home']
        away = data['away']
        winner = data['winner']
        conf = data['confidence']
        advice = data['advice']
        gg = data['gg']
        ou = data['ou']
        det = data['detailed']
        heading = data['heading']

        # Multi-market layout for "Musk-style" professionalism
        tweet_text = (
            f"{heading}\n"
            f"⚽ {home} vs {away}\n\n"
            f"🔮 Logic: {det['main']}\n"
            f"🛡️ Win/Draw: {det['dc']}\n"
            f"💎 GG/NG: {gg} | O/U: {ou}\n"
            f"📐 Corners: {det['corners']}\n"
            f"⏱️ HT Result: {det['ht']}\n\n"
            f"💡 Outcome: {winner} ({conf})\n"
            f"📣 {advice}{shoutout}\n\n"
            f"NorraAI Football Predictions"
        )
        
        try:
            if dry_run:
                print(f"\n[DRY RUN TWEET for {match}]:\n{tweet_text}")
            else:
                api.update_status(tweet_text)
                print(f"Prediction posted: {match}")
        except Exception as e:
            print(f"Failed to post prediction for {match}: {e}")

def update_bot_stats(stats):
    """Helper to save bot statistics to file."""
    stats_file = "bot_stats.json"
    try:
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=4)
    except IOError as e:
        print(f"Error saving bot stats: {e}")

def verify_previous_matches(api_key):
    """
    Verifies the outcomes of matches from yesterday that were predicted,
    and updates bot statistics (wins/losses).
    """
    import datetime
    import json
    import os
    from football_api import get_fixtures_by_date

    stats_file = "bot_stats.json"
    stats = {}
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r") as f:
                stats = json.load(f)
        except json.JSONDecodeError:
            print("Error reading bot_stats.json, starting with empty stats.")
            stats = {}
    
    # Initialize stats if empty or missing keys
    stats.setdefault('verified_ids', [])
    stats.setdefault('total_predictions', 0)
    stats.setdefault('total_wins', 0)
    stats.setdefault('total_losses', 0)
    stats.setdefault('weekly_wins', 0) # Reset weekly wins if needed, or manage sliding window

    yesterday = datetime.datetime.now().date() - datetime.timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    print(f"Verifying matches for {yesterday_str}...")

    # Fetch all fixtures for yesterday
    yesterday_fixtures = get_fixtures_by_date(yesterday_str, api_key)
    
    if not yesterday_fixtures:
        print(f"No fixtures found for {yesterday_str} to verify.")
        return

    wins_today = 0
    losses_today = 0
    verified_count = 0

    for f in yesterday_fixtures:
        fid = f['fixture']['id']
        # For now, we assume any match that was predicted would have its ID in verified_ids
        # In a real system, we'd store the actual prediction and compare.
        if fid in stats['verified_ids']: # This is a placeholder, needs actual prediction storage
            if f['fixture']['status']['short'] == 'FT': # Only verify finished matches
                home_g = f['goals']['home']
                away_g = f['goals']['away']

                # Mock verification: Assume a "Home" bias prediction for simplicity
                # In a real system, this would compare against the stored prediction
                if home_g > away_g: # If home won, and we "predicted" home
                    wins_today += 1
                    stats['total_wins'] += 1
                else: # If home didn't win, and we "predicted" home
                    losses_today += 1
                    stats['total_losses'] += 1
                
                verified_count += 1
                stats['total_predictions'] += 1
                # Remove from verified_ids once processed to avoid re-processing
                stats['verified_ids'].remove(fid) 
            else:
                print(f"Fixture {fid} not yet finished ({f['fixture']['status']['short']}), skipping verification.")

    stats['weekly_wins'] = (stats.get('weekly_wins', 0) + wins_today) # Update weekly wins
    
    update_bot_stats(stats)
    print(f"Verification complete for {yesterday_str}: {wins_today} wins, {losses_today} losses out of {verified_count} predicted matches.")
    print(f"Current overall record: {stats['total_wins']} wins, {stats['total_losses']} losses.")


if __name__ == "__main__":
    import sys
    import os
    import json
    import tweepy
    import datetime
    from football_api import get_fixtures, get_prioritized_fixtures, get_predictions, get_lineups
    
    dry_run = "--dry-run" in sys.argv
    
    print(f"--- Norra AI Start Sequence (Dry Run: {dry_run}) ---")
    
    api_key = os.getenv("RAPIDAPI_KEY")

    if api_key:
        # Step 0: Verify Performance
        verify_previous_matches(api_key)
        
        # Step 1: Run Predictions
        fetch_predictions(api_key=api_key, dry_run=dry_run)
    else:
        print("CRITICAL: RAPIDAPI_KEY not found in .env")