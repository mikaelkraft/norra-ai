import datetime
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import numpy as np
import tweepy
from football_api import get_fixtures
import database
from database import SessionLocal, Prediction
import telegram_bot
import json


# API_football Actual API credentials and league ID
api_key = os.getenv("FOOTBALL_API_KEY")
# List of leagues with their IDs (updated for 2025/26 seasons)
leagues = [
    # Tier 1 & Major Internationals
    {"league_id": 39, "season": 2025, "name": "Premier League"},
    {"league_id": 140, "season": 2025, "name": "La Liga"},
    {"league_id": 135, "season": 2025, "name": "Serie A"},
    {"league_id": 78, "season": 2025, "name": "Bundesliga"},
    {"league_id": 61, "season": 2025, "name": "Ligue 1"},
    {"league_id": 94, "season": 2025, "name": "Primeira Liga"},
    {"league_id": 88, "season": 2025, "name": "Eredivisie"},
    {"league_id": 203, "season": 2025, "name": "Super Lig"},
    {"league_id": 253, "season": 2025, "name": "MLS"},
    {"league_id": 307, "season": 2025, "name": "Saudi Pro League"},
    {"league_id": 71, "season": 2025, "name": "Brasileirao"},
    {"league_id": 128, "season": 2025, "name": "Liga Profesional"},
    {"league_id": 262, "season": 2025, "name": "Liga MX"},
    {"league_id": 179, "season": 2025, "name": "Premiership"},
    
    # Continents
    {"league_id": 2, "season": 2025, "name": "UCL"},
    {"league_id": 3, "season": 2025, "name": "UEL"},
    {"league_id": 848, "season": 2025, "name": "UECL"},
    {"league_id": 6, "season": 2025, "name": "AFCON"},
    
    # Tier 2 & Fallbacks
    {"league_id": 40, "season": 2025, "name": "Championship"},
    {"league_id": 141, "season": 2025, "name": "Segunda"},
    {"league_id": 136, "season": 2025, "name": "Serie B"},
    {"league_id": 79, "season": 2025, "name": "2. Bundesliga"},
    {"league_id": 62, "season": 2025, "name": "Ligue 2"},
    {"league_id": 144, "season": 2025, "name": "Pro League"},
    {"league_id": 113, "season": 2025, "name": "Allsvenskan"},
    {"league_id": 119, "season": 2025, "name": "Superliga"},
    {"league_id": 188, "season": 2025, "name": "A-League"},
    {"league_id": 98, "season": 2025, "name": "J1 League"},
    {"league_id": 305, "season": 2025, "name": "Qatar Stars League"},
    {"league_id": 235, "season": 2025, "name": "Russian Premier"}
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
    # Authenticate with direct Football API (API-Sports)
    api_key = os.getenv("FOOTBALL_API_KEY") 
    print(f"Connecting to API-Sports...")
    current_date = datetime.datetime.now().date()

    # Wholesome ML Training (Persistent & Incremental)
    try:
        from prediction_model import fetch_training_data, train_model
        # Use all global leagues for training context (saved locally in training_data.csv)
        training_leagues = [l["league_id"] for l in leagues]
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
            "league_name": league_name,
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
def get_twitter_api():
    """Authenticates and returns the Tweepy API object."""
    consumer_key = os.getenv("X_CONSUMER_KEY")
    consumer_secret = os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    
    try:
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth)
        if api.verify_credentials():
            return api
        else:
            print("Twitter authentication failed. Check credentials.")
    except Exception as e:
        print(f"Twitter auth error: {e}")
    return None

def post_predictions(predictions, dry_run=False):
    """Posts predictions to X, managing rate limits and standalone achievements."""
    import json
    stats_file = "bot_stats.json"
    stats = {}
    if os.path.exists(stats_file):
        with open(stats_file, "r") as f:
            stats = json.load(f)
    
    # --- Rate Limit Management ---
    current_month = datetime.datetime.now().strftime("%Y-%m")
    last_reset = stats.get("last_reset_month", "")
    
    if current_month != last_reset:
        stats["monthly_posts_count"] = 0
        stats["last_reset_month"] = current_month
        print(f"Monthly post counter reset for {current_month}")

    post_limit = 500
    posts_remaining = post_limit - stats.get("monthly_posts_count", 0)
    print(f"X API Posts Remaining for this month: {posts_remaining}/{post_limit}")

    if posts_remaining <= 0 and not dry_run:
        print("CRITICAL: Monthly X post limit reached. Skipping posts.")
        return

    # Authenticate once to save "Reads" quota
    api = None
    if not dry_run:
        api = get_twitter_api()
        if not api:
            print("X authentication failed. Aborting post sequence.")
            return

    # --- Smart Rate Management: Engagement Check ---
    # Disable non-essential activities if below 5% quota
    engagement_safe = posts_remaining > (post_limit * 0.05)
    if not engagement_safe:
        print("WARNING: Low rate limit ( < 5%). Mode: Conservative (Predictions Only).")

    # --- Standalone Achievement Shoutout ---
    weekly_wins = stats.get("weekly_wins", 0)
    last_shoutout = stats.get("last_shoutout_date", "")
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    if weekly_wins >= 5 and last_shoutout != today_str:
        achievement_text = (
            f"🔥 NorraAI ACHIEVEMENT UNLOCKED\n\n"
            f"The bot is on absolute fire with a 5/7 winning streak this week! 🎯\n\n"
            f"Consistency is key. Near-perfect predictions rolling out now.\n\n"
            f"NorraAI Football Predictions"
        )
        if not dry_run and engagement_safe: # Only post if not dry run AND engagement is safe
            try:
                if api:
                    api.update_status(achievement_text)
                    stats["monthly_posts_count"] = stats.get("monthly_posts_count", 0) + 1
                    stats["last_shoutout_date"] = today_str
                    update_bot_stats(stats)
                    print("Achievement shoutout posted as a separate tweet!")
            except Exception as e:
                print(f"Failed to post achievement tweet: {e}")
        else:
            print(f"\n[DRY RUN ACHIEVEMENT TWEET]:\n{achievement_text}")

    # --- Post Match Predictions ---
    for match, data in predictions.items():
        # Re-check limit inside loop
        if not dry_run and stats.get("monthly_posts_count", 0) >= post_limit:
            print("Monthly limit hit mid-batch. Stopping.")
            break

        home = data['home']
        away = data['away']
        winner = data['winner']
        conf = data['confidence']
        advice = data['advice']
        gg = data['gg']
        ou = data['ou']
        det = data['detailed']
        heading = data['heading']

        tweet_text = (
            f"{heading}\n"
            f"⚽ {home} vs {away}\n\n"
            f"🔮 Logic: {det['main']}\n"
            f"🛡️ Win/Draw: {det['dc']}\n"
            f"💎 Goal Forecast: {det['ou_refined']}\n"
            f"🌟 Star Power: {det['star_power']}\n"
            f"⏱️ HT Result: {det['ht']}\n\n"
            f"💡 Outcome: {winner} ({conf})\n"
            f"📣 {advice}\n\n"
            f"NorraAI Prediction Beacon Force"
        )
        
        try:
            if dry_run:
                print(f"\n[DRY RUN TWEET for {match}]:\n{tweet_text}")
            else:
                if api:
                    api.update_status(tweet_text)
                    stats["monthly_posts_count"] = stats.get("monthly_posts_count", 0) + 1
                    
                    # --- Record Prediction for Verification ---
                    # We store the fixture_id and our expected winner for tomorrow's verification
                    if "predictions_to_verify" not in stats:
                        stats["predictions_to_verify"] = {}
                    
                    # Store as: {fixture_id: predicted_winner_type}
                    # winner_type: "Home", "Away", "Draw"
                    winner_type = "Home" if winner == home else ("Away" if winner == away else "Draw")
                    stats["predictions_to_verify"][str(data['fixture_id'])] = winner_type
                    
                    update_bot_stats(stats)
                    print(f"Prediction posted: {match}")

                # --- Sync to Ecosystem Database (Persistent) ---
                db = SessionLocal()
                try:
                    # Check if fixture already exists to avoid duplicates
                    existing = db.query(Prediction).filter(Prediction.fixture_id == data['fixture_id']).first()
                    if not existing:
                        new_pred = Prediction(
                            fixture_id=data['fixture_id'],
                            home_team=home,
                            away_team=away,
                            league_name=data.get('league_name', 'Global League'),
                            prediction_main=winner,
                            confidence=conf,
                            dc=det['dc'],
                            ht=det['ht'],
                            ou_refined=det['ou_refined'],
                            star_power=det['star_power'],
                            h2h_dom=det['h2h_dom']
                        )
                        db.add(new_pred)
                        db.commit()
                        print(f"Prediction synced to database: {match}")
                except Exception as e:
                    print(f"Database sync failed for {match}: {e}")
                finally:
                    db.close()

        except Exception as e:
            print(f"Failed to post/sync prediction for {match}: {e}")

    # --- Eco-System Broadcast (Telegram) ---
    # After all predictions are posted/synced, broadcast the daily picks to Telegram
    if not dry_run:
        try:
            telegram_bot.broadcast_predictions()
        except Exception as e:
            print(f"Telegram broadcast trigger failed: {e}")

    # --- GitHub Pages Sync (Serverless) ---
    # Export predictions to a flat JSON file for hosting on GitHub Pages
    save_predictions_to_json(predictions)

def save_predictions_to_json(predictions):
    """Saves predictions to a flat JSON file for GitHub Pages."""
    output_file = "predictions.json"
    last_updated = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    formatted_preds = []
    for match, data in predictions.items():
        det = data['detailed']
        formatted_preds.append({
            "fixture_id": data['fixture_id'],
            "home": data['home'],
            "away": data['away'],
            "league": data.get('league_name', 'Global League'),
            "main": data['winner'],
            "conf": data['confidence'],
            "dc": det['dc'],
            "ht": det['ht'],
            "ou": det['ou_refined'],
            "stars": det['star_power'],
            "h2h": det['h2h_dom'],
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    
    try:
        data_to_save = {
            "last_updated": last_updated,
            "predictions": formatted_preds
        }
        with open(output_file, "w") as f:
            json.dump(data_to_save, f, indent=4)
        print(f"Predictions exported with metadata to {output_file}.")
    except Exception as e:
        print(f"Failed to export JSON for GitHub Pages: {e}")

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
    from football_api import get_fixture_by_id

    stats_file = "bot_stats.json"
    stats = {}
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r") as f:
                stats = json.load(f)
        except:
            return

    # Initialize keys
    stats.setdefault('predictions_to_verify', {})
    stats.setdefault('weekly_wins', 0)
    stats.setdefault('verified_ids', [])

    if not stats['predictions_to_verify']:
        print("No pending predictions to verify.")
        return

    print(f"\n--- Verifying {len(stats['predictions_to_verify'])} Pending Matches ---")
    
    pending_ids = list(stats['predictions_to_verify'].keys())
    wins_added = 0
    total_checked = 0

    for fid in pending_ids:
        fixture = get_fixture_by_id(fid, api_key)
        if not fixture: continue
        
        status = fixture['fixture']['status']['short']
        if status == 'FT':
            total_checked += 1
            home_g = fixture['goals']['home']
            away_g = fixture['goals']['away']
            actual_winner = "Home" if home_g > away_g else ("Away" if away_g > home_g else "Draw")
            
            predicted_winner = stats['predictions_to_verify'][fid]
            
            if predicted_winner == actual_winner or (predicted_winner == "Draw" and home_g == away_g):
                wins_added += 1
                print(f"✅ Match {fid}: Correct! ({predicted_winner})")
            else:
                print(f"❌ Match {fid}: Incorrect. Predicted {predicted_winner}, Result {actual_winner}")
            
            # Move to historical verification log and remove from pending
            stats['verified_ids'].append(fid)
            del stats['predictions_to_verify'][fid]
        else:
            print(f"⏳ Match {fid}: Still pending ({status}).")

    if total_checked > 0:
        # Update weekly win streak (sliding window of 7 days would be complex, 
        # using a simple increment for now)
        stats['weekly_wins'] = stats.get('weekly_wins', 0) + wins_added
        
        # Reset weekly wins if more than a week passed (simplified)
        last_reset = stats.get("last_weekly_reset", "")
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        if last_reset != today_str and datetime.datetime.now().weekday() == 0: # Monday reset
            stats["weekly_wins"] = wins_added # Reset to current week's wins
            stats["last_weekly_reset"] = today_str

    update_bot_stats(stats)
    print(f"Verification complete. Total Wins this week: {stats['weekly_wins']}/7 mission target.")


if __name__ == "__main__":
    import sys
    import os
    import json
    import tweepy
    import datetime
    from football_api import get_fixtures, get_prioritized_fixtures, get_predictions, get_lineups
    
    dry_run = "--dry-run" in sys.argv
    
    print(f"--- Norra AI Start Sequence (Dry Run: {dry_run}) ---")
    
    api_key = os.getenv("FOOTBALL_API_KEY")

    if api_key:
        # Step 0: Initialize Database
        database.init_db()
        
        # Step 1: Verify Performance
        verify_previous_matches(api_key)
        
        # Step 1: Run Predictions
        fetch_predictions(api_key=api_key, dry_run=dry_run)
    else:
        print("CRITICAL: FOOTBALL_API_KEY not found in .env")