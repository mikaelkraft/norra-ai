
import os
import datetime
import json
from dotenv import load_dotenv

# Mocking parts of Norra.py for verification
def update_bot_stats(stats):
    with open("bot_stats_test.json", "w") as f:
        json.dump(stats, f, indent=4)

def mock_get_twitter_api():
    print("DEBUG: Twitter API Authenticated (Mock)")
    class MockAPI:
        def update_status(self, text):
            print(f"\n[POSTED TO X]:\n{text}")
        def verify_credentials(self):
            return True
    return MockAPI()

# Test Logic
def test_rate_limit_and_achievement():
    stats = {
        "monthly_posts_count": 498,
        "last_reset_month": "2026-01",
        "weekly_wins": 5,
        "last_shoutout_date": "2026-01-08"
    }
    with open("bot_stats_test.json", "w") as f:
        json.dump(stats, f)
    
    # Simulate first post (Achievement)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    weekly_wins = stats.get("weekly_wins", 0)
    last_shoutout = stats.get("last_shoutout_date", "")
    
    if weekly_wins >= 5 and last_shoutout != today_str:
        achievement_text = "Achievement: 5/7 winning streak!"
        mock_get_twitter_api().update_status(achievement_text)
        stats["monthly_posts_count"] += 1
        stats["last_shoutout_date"] = today_str
        update_bot_stats(stats)
        print(f"Achievement Posted. Count: {stats['monthly_posts_count']}")

    # Simulate Prediction Post
    prediction_posted = False
    if stats["monthly_posts_count"] < 500:
        prediction_text = "Match Prediction: Home Win"
        mock_get_twitter_api().update_status(prediction_text)
        stats["monthly_posts_count"] += 1
        update_bot_stats(stats)
        prediction_posted = True
        print(f"Prediction Posted. Count: {stats['monthly_posts_count']}")
    
    # Simulate second Prediction Post (should hit limit)
    if stats["monthly_posts_count"] < 500:
        print("Posting second prediction...")
    else:
        print("CRITICAL: Rate limit reached as expected (500/500).")

if __name__ == "__main__":
    test_rate_limit_and_achievement()
