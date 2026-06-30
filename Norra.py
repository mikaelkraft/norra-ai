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
from database import SessionLocal, Prediction, BotStats, PostTimeline
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
    print("Running predictions engine (Local DB + ESPN mode)...")
    
    # 1. Update current season match played database (fetch latest played results)
    try:
        from prediction_model import update_current_season_matches
        update_current_season_matches()
    except Exception as e:
        print(f"Failed to update current season matches: {e}")

    # 2. Train the ML model on local DB data
    try:
        from prediction_model import fetch_training_data, train_model
        training_leagues = [l["league_id"] for l in leagues]
        train_df = fetch_training_data(None, training_leagues)
        model = train_model(train_df)
    except Exception as e:
        print(f"ML Training failed, falling back to rule-engine: {e}")
        model = None

    # 3. Fetch today's fixtures using free ESPN scoreboard API
    from espn_api import fetch_combined_today_fixtures
    try:
        raw_fixtures = fetch_combined_today_fixtures()
    except Exception as e:
        print(f"Failed to fetch fixtures from ESPN Scoreboard: {e}")
        return

    if not raw_fixtures:
        print("No matches found on ESPN Scoreboard today.")
        return

    # 4. Convert ESPN fixtures to mock API-Football dictionary format
    fixtures = []
    for f in raw_fixtures:
        season_val = 2025
        for l in leagues:
            if l["league_id"] == f["league_id"]:
                season_val = l["season"]
                break
        
        mocked_fixture = {
            "fixture": {
                "id": hash(f"{f['home']}_{f['away']}_{f['league_id']}") % 10000000,
                "venue": {
                    "name": "Main Stadium",
                    "city": "Unknown"
                },
                "weather": {
                    "description": "clear sky",
                    "temp": 20
                },
                "referee": "Standard Referee"
            },
            "teams": {
                "home": {
                    "id": hash(f['home']) % 10000,
                    "name": f['home']
                },
                "away": {
                    "id": hash(f['away']) % 10000,
                    "name": f['away']
                }
            },
            "league": {
                "id": f['league_id'],
                "name": f['espn_league'],
                "season": season_val
            }
        }
        fixtures.append(mocked_fixture)

    # 5. Process fetched fixtures and generate predictions
    predictions = generate_predictions(fixtures, None, model=model)
    
    # 6. Post predictions to X
    post_predictions(predictions, dry_run=dry_run)

def generate_dynamic_advice(home, away, detailed_data):
    outcome = detailed_data.get("main", "Draw / Very Close")
    confidence_str = detailed_data.get("confidence", "50%")
    try:
        confidence = float(confidence_str.replace("%", "").strip())
    except ValueError:
        confidence = 50.0
        
    btts = detailed_data.get("btts", "NG / No")
    ou = detailed_data.get("ou_refined", "Under 2.5")
    dnb = detailed_data.get("dnb", "1 DNB")
    dc = detailed_data.get("dc", "1X / 2X")
    combos = detailed_data.get("combos", "")
    
    if "win" in outcome.lower():
        winner_team = home if ("home" in outcome.lower() or home.lower() in outcome.lower()) else away
        if confidence >= 80.0:
            return f"Ultra High Conviction: Straight win for {winner_team} is highly recommended. For safer play, select {winner_team} Draw No Bet ({dnb})."
        elif confidence >= 70.0:
            return f"High Conviction: Strong stats favoring {winner_team}. Recommended selection: {winner_team} Win or {winner_team} Draw No Bet ({dnb})."
        else:
            return f"Moderate Conviction: Favors {winner_team} but stats show close margins. Safe selection: Double Chance {dc} or combo bet: {combos}."
    else:
        if "over 2.5" in ou.lower() or "gg" in btts.lower():
            return f"Close Match: Competitive draw risk. Best selections are in goals/GG markets: Over 1.5/2.5 goals ({ou}) or Both Teams to Score ({btts})."
        else:
            return f"Defensive Close Match: Low-scoring draw risk. Best selections: Under 2.5 goals ({ou}) or Double Chance {dc}."

def generate_predictions(fixtures, api_key, model=None):
    """
    Richer prediction generation using local DB stats and ML.
    """
    from prediction_model import get_match_prediction
    predictions = {}

    for fixture in fixtures:
        fixture_id = fixture['fixture']['id']
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        
        # Native API predictions are not used (API-Football is bypassed)
        advice = "No specific advice"
        winner = "Unknown"
        conf = "50%"
        gg_outcome = "N/A"
        ou_outcome = "N/A"

        # Get Hybrid ML + Rule-Engine Prediction locally
        detailed_data = get_match_prediction(fixture, None, model=model)
        
        league_name = fixture['league']['name']
        venue = fixture['fixture'].get('venue', {}).get('name', 'Main Stadium')
        location = fixture['fixture'].get('venue', {}).get('city', 'Unknown')

        result_key = f"{home_team} vs {away_team}"
        
        rf_winner = detailed_data.get("main", winner)
        rf_confidence = detailed_data.get("confidence", conf)
        rf_gg = detailed_data.get("btts", gg_outcome)
        rf_ou = detailed_data.get("ou_refined", ou_outcome)
        rf_advice = generate_dynamic_advice(home_team, away_team, detailed_data)

        predictions[result_key] = {
            "fixture_id": fixture_id,
            "league_name": league_name,
            "winner": rf_winner,
            "confidence": rf_confidence,
            "advice": rf_advice,
            "home": home_team,
            "away": away_team,
            "gg": rf_gg,
            "ou": rf_ou,
            "heading": f"🏆 NorraAI MATCHDAY: {league_name} | {venue}",
            "detailed": detailed_data
        }

    return predictions
def get_twitter_client():
    """Authenticates and returns the Tweepy Client object (API v2)."""
    consumer_key = os.getenv("X_CONSUMER_KEY")
    consumer_secret = os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    
    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("Twitter credentials incomplete in environment variables.")
        return None
        
    try:
        # Tweepy Client uses API v2 which is supported on Free Tier
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        return client
    except Exception as e:
        print(f"Twitter client init error: {e}")
    return None

def load_bot_stats():
    """Loads bot statistics from the database, falling back to JSON or default stats."""
    db = SessionLocal()
    try:
        record = db.query(BotStats).filter(BotStats.key == "global_stats").first()
        if record and record.data:
            return record.data
    except Exception as e:
        print(f"Failed to load bot stats from DB: {e}")
    finally:
        db.close()
        
    # Fallback to local file if available
    stats_file = "bot_stats.json"
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to read local stats file fallback: {e}")
            
    # Default stats schema
    return {
        "monthly_posts_count": 0,
        "last_reset_month": datetime.datetime.now().strftime("%Y-%m"),
        "weekly_wins": 0,
        "predictions_to_verify": {}
    }

def update_bot_stats(stats):
    """Helper to save bot statistics to the database (and local file fallback)."""
    db = SessionLocal()
    try:
        record = db.query(BotStats).filter(BotStats.key == "global_stats").first()
        if not record:
            record = BotStats(key="global_stats", data=stats)
            db.add(record)
        else:
            record.data = stats
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(record, "data")
        db.commit()
        print("Bot stats updated in database.")
    except Exception as e:
        db.rollback()
        print(f"Error saving bot stats to database: {e}")
    finally:
        db.close()

    # Still write locally as fallback
    stats_file = "bot_stats.json"
    try:
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=4)
    except IOError as e:
        print(f"Error saving bot stats fallback file: {e}")

def post_predictions(predictions, dry_run=False):
    """Posts predictions to X using Tweepy API v2, managing rate limits and standalone achievements."""
    stats = load_bot_stats()
    
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

    # Authenticate once to save quota/verify setup
    client = None
    if not dry_run:
        client = get_twitter_client()
        if not client:
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
        if not dry_run and engagement_safe:
            try:
                if client:
                    client.create_tweet(text=achievement_text)
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
        
        def parse_confidence(conf_str):
            try:
                return float(str(conf_str).replace('%', ''))
            except:
                return 50.0

        try:
            post_threshold = float(os.getenv("POST_CONFIDENCE_THRESHOLD", "70.0"))
        except ValueError:
            post_threshold = 70.0

        is_high_confidence = parse_confidence(conf) >= post_threshold

        if is_high_confidence:
            if dry_run:
                print(f"\n[DRY RUN TWEET for {match}]:\n{tweet_text}")
            else:
                tweet_link = None
                x_posted = False
                tg_posted = False
                
                # 1. Post to X
                if client:
                    try:
                        response = client.create_tweet(text=tweet_text)
                        stats["monthly_posts_count"] = stats.get("monthly_posts_count", 0) + 1
                        
                        if "predictions_to_verify" not in stats:
                            stats["predictions_to_verify"] = {}
                        winner_type = "Home" if winner == home else ("Away" if winner == away else "Draw")
                        stats["predictions_to_verify"][str(data['fixture_id'])] = winner_type
                        update_bot_stats(stats)
                        
                        tweet_id = response.data.get("id") if response.data else None
                        tweet_link = f"https://x.com/user/status/{tweet_id}" if tweet_id else None
                        x_posted = True
                        print(f"Prediction posted to X: {match}")
                    except Exception as x_err:
                        print(f"Auto-post to X failed: {x_err}")

                # 2. Broadcast to Telegram
                import telegram_bot
                if telegram_bot.bot and telegram_bot.TELEGRAM_CHANNEL_ID:
                    try:
                        telegram_bot.bot.send_message(telegram_bot.TELEGRAM_CHANNEL_ID, tweet_text, parse_mode="Markdown")
                        tg_posted = True
                        print(f"Prediction broadcast to Telegram: {match}")
                    except Exception as tg_err:
                        print(f"Auto-broadcast to Telegram failed: {tg_err}")

                # 3. Always log to local timeline database!
                db_session = SessionLocal()
                try:
                    if client:
                        x_record = PostTimeline(
                            fixture_id=data['fixture_id'],
                            platform="X",
                            content=tweet_text,
                            link=tweet_link
                        )
                        db_session.add(x_record)
                    
                    if telegram_bot.bot and telegram_bot.TELEGRAM_CHANNEL_ID:
                        tg_record = PostTimeline(
                            fixture_id=data['fixture_id'],
                            platform="Telegram",
                            content=tweet_text
                        )
                        db_session.add(tg_record)
                        
                    db_session.commit()
                    print(f"Picks synced to timeline feed database: {match}")
                except Exception as db_err:
                    db_session.rollback()
                    print(f"Timeline DB Sync Failed: {db_err}")
                finally:
                    db_session.close()
        else:
            print(f"Confidence {conf} is below 90% threshold for {match}. Skipped auto-post.")

        # --- Sync to Ecosystem Database (Persistent) - Always run for all predictions ---
        db = SessionLocal()
        try:
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
                    btts=det['btts'],
                    dnb=det['dnb'],
                    multi_goals=det['multi_goals'],
                    ht_ft=det['ht_ft'],
                    combos=det['combos'],
                    star_power=det['star_power'],
                    h2h_dom=det['h2h_dom'],
                    league_avg_goals=det['league_avg_goals']
                )
                db.add(new_pred)
                db.commit()
                print(f"Prediction synced to database: {match}")
        except Exception as e:
            print(f"Database sync failed for {match}: {e}")
        finally:
            db.close()

    # Telegram broadcasting is now handled inside the loop for high-confidence predictions.
    # We disable the global broadcast to avoid duplicate broadcasts.

    # --- GitHub Pages Sync (Serverless fallback) ---
    save_predictions_to_json(predictions)

def save_predictions_to_json(predictions):
    """Saves predictions to a flat JSON file for GitHub Pages (local fallback)."""
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

def verify_previous_matches(api_key):
    """
    Verifies the outcomes of matches from yesterday that were predicted,
    and updates bot statistics (wins/losses) using local played_matches.
    """
    import datetime
    import json
    import os
    from prediction_model import standardize_team_name

    stats = load_bot_stats()

    stats.setdefault('predictions_to_verify', {})
    stats.setdefault('weekly_wins', 0)
    stats.setdefault('verified_ids', [])

    if not stats['predictions_to_verify']:
        print("No pending predictions to verify.")
        return

    print(f"\n--- Verifying {len(stats['predictions_to_verify'])} Pending Matches locally ---")
    
    pending_ids = list(stats['predictions_to_verify'].keys())
    wins_added = 0
    total_checked = 0
    
    db = SessionLocal()
    try:
        for fid in pending_ids:
            pred_record = db.query(Prediction).filter(Prediction.fixture_id == int(fid)).first()
            if not pred_record:
                stats['verified_ids'].append(fid)
                del stats['predictions_to_verify'][fid]
                continue
                
            home_std = standardize_team_name(pred_record.home_team)
            away_std = standardize_team_name(pred_record.away_team)
            
            recent_matches = db.query(database.PlayedMatch).filter(
                database.PlayedMatch.match_date >= datetime.datetime.utcnow() - datetime.timedelta(days=4)
            ).all()
            
            played_fixture = None
            for rm in recent_matches:
                rm_home_std = standardize_team_name(rm.home_team)
                rm_away_std = standardize_team_name(rm.away_team)
                if rm_home_std == home_std and rm_away_std == away_std:
                    played_fixture = rm
                    break
                    
            if not played_fixture:
                print(f"[PENDING] Match {fid} ({pred_record.home_team} vs {pred_record.away_team}): Still pending / not found in played matches.")
                continue
                
            total_checked += 1
            home_g = played_fixture.home_goals
            away_g = played_fixture.away_goals
            actual_winner = "Home" if home_g > away_g else ("Away" if away_g > home_g else "Draw")
            
            predicted_winner = stats['predictions_to_verify'][fid]
            
            is_correct = False
            if predicted_winner == "Draw" or "Draw" in predicted_winner:
                if home_g == away_g:
                    is_correct = True
            elif "home" in predicted_winner.lower() or pred_record.home_team.lower() in predicted_winner.lower():
                if home_g > away_g:
                    is_correct = True
            elif "away" in predicted_winner.lower() or pred_record.away_team.lower() in predicted_winner.lower():
                if away_g > home_g:
                    is_correct = True
                    
            if is_correct:
                wins_added += 1
                print(f"[SUCCESS] Match {fid} ({pred_record.home_team} vs {pred_record.away_team}): Correct! ({predicted_winner})")
            else:
                print(f"[FAIL] Match {fid} ({pred_record.home_team} vs {pred_record.away_team}): Incorrect. Predicted {predicted_winner}, Result {actual_winner} ({home_g}-{away_g})")
            
            stats['verified_ids'].append(fid)
            del stats['predictions_to_verify'][fid]
    except Exception as e:
        print(f"Failed to verify previous matches: {e}")
    finally:
        db.close()

    if total_checked > 0:
        stats['weekly_wins'] = stats.get('weekly_wins', 0) + wins_added
        
        last_reset = stats.get("last_weekly_reset", "")
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        if last_reset != today_str and datetime.datetime.now().weekday() == 0:
            stats["weekly_wins"] = wins_added
            stats["last_weekly_reset"] = today_str

    update_bot_stats(stats)
    print(f"Verification complete. Total Wins this week: {stats['weekly_wins']}/7 mission target.")


if __name__ == "__main__":
    import sys
    import os
    import json
    import tweepy
    import datetime
    
    dry_run = "--dry-run" in sys.argv
    
    print(f"--- Norra AI Start Sequence (Dry Run: {dry_run}) ---")
    
    # Step 0: Initialize Database
    database.init_db()
    
    # Step 1: Verify Performance
    verify_previous_matches(None)
    
    # Step 2: Run Predictions
    fetch_predictions(api_key=None, dry_run=dry_run)