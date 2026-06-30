import os
import telebot
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import database
from database import SessionLocal, Prediction, PostTimeline

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

bot = None
if TELEGRAM_TOKEN:
    try:
        bot = telebot.TeleBot(TELEGRAM_TOKEN)
    except Exception as e:
        print(f"Failed to initialize TeleBot: {e}")
else:
    print("WARNING: TELEGRAM_BOT_TOKEN is missing in environment variables. Telegram notifications are disabled.")

def broadcast_predictions():
    """Broadcasts today's top predictions to the Telegram channel."""
    if not bot or not TELEGRAM_CHANNEL_ID:
        print("Telegram credentials missing or uninitialized.")
        return

    db = SessionLocal()
    try:
        predictions = db.query(database.Prediction).order_by(database.Prediction.created_at.desc()).limit(5).all()

        if not predictions:
            print("No predictions found to broadcast.")
            return

        message = "🛰️ **NorraAI BEACON FORCE | TOP PICKS**\n\n"
        for p in predictions:
            message += f"⚽ **{p.home_team} vs {p.away_team}**\n"
            message += f"🔮 Logic: {p.prediction_main}\n"
            message += f"🛡️ DC: {p.dc} | 💎 O/U: {p.ou_refined}\n"
            message += f"⏱️ HT: {p.ht} | 🌟 Stars: {p.star_power}\n\n"

        message += "🔗 [Visit Web Dashboard](https://mikaelkraft.github.io/norra-ai)\n"
        message += "NorraAI Prediction Beacon Force"

        bot.send_message(TELEGRAM_CHANNEL_ID, message, parse_mode="Markdown")
        print("Telegram broadcast successful!")
    except Exception as e:
        print(f"Telegram broadcast failed: {e}")
    finally:
        db.close()

if bot:
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(message, "Welcome to Norra AI! Use /today to get latest mathematical forecasts.")

    @bot.message_handler(commands=['today'])
    def send_predictions(message):
        args = message.text.split()
        db = SessionLocal()
        try:
            # Check if the user specified a team (e.g. "/today Arsenal")
            if len(args) > 1:
                query = " ".join(args[1:]).lower().strip()
                # 1. Search existing predictions
                predictions = db.query(database.Prediction).filter(
                    (database.Prediction.home_team.ilike(f"%{query}%")) |
                    (database.Prediction.away_team.ilike(f"%{query}%"))
                ).order_by(database.Prediction.created_at.desc()).limit(1).all()
                
                # 2. If not found, trigger on-demand generation using free ESPN Scoreboard & API-Football
                    if not predictions:
                        bot.reply_to(message, f"❌ I couldn't find any active predictions for '{query.capitalize()}' in my database right now. Predictions are generated daily by our automated system. Please check the website timeline, or try again later when predictions are updated!")
                        return
            else:
                # Default to top 5 recent predictions
                predictions = db.query(database.Prediction).order_by(database.Prediction.created_at.desc()).limit(5).all()
            
            if not predictions:
                bot.reply_to(message, "No active beacons found.")
                return
                
            resp = "🛰️ **NorraAI BEACON FORCE FORECASTS**\n\n"
            for p in predictions:
                resp += f"⚽ **{p.home_team} vs {p.away_team}** ({p.league_name})\n"
                resp += f"🔮 Outcome: {p.prediction_main} ({p.confidence})\n"
                resp += f"🛡️ DC: {p.dc} | 💎 Goals: {p.ou_refined}\n"
                resp += f"⏱️ HT: {p.ht} | 🌟 Stars: {p.star_power}\n\n"
                
            bot.send_message(message.chat.id, resp, parse_mode="Markdown")
        finally:
            db.close()

    @bot.message_handler(commands=['timeline'])
    def get_timeline_posts(message):
        db = SessionLocal()
        try:
            posts = db.query(PostTimeline).order_by(PostTimeline.created_at.desc()).limit(5).all()
            if not posts:
                bot.reply_to(message, "No posts logged in the timeline feed database.")
                return
                
            resp = "🛰️ **Recent Broadcast Timeline Posts:**\n\n"
            for p in posts:
                resp += f"🆔 **ID: {p.id}** | Platform: {p.platform}\n"
                resp += f"📝 {p.content[:150]}...\n\n"
            resp += "Use `/repost <id>` to rebroadcast any pick to the main channel!"
            bot.send_message(message.chat.id, resp, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Database error: {e}")
        finally:
            db.close()

    @bot.message_handler(commands=['repost'])
    def repost_post(message):
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Usage: `/repost <id>`")
            return
            
        post_id = args[1]
        db = SessionLocal()
        try:
            post = db.query(PostTimeline).filter(PostTimeline.id == post_id).first()
            if not post:
                bot.reply_to(message, f"Post with ID {post_id} not found.")
                return
                
            bot.send_message(TELEGRAM_CHANNEL_ID, post.content, parse_mode="Markdown")
            bot.reply_to(message, f"🎯 Rebroadcasted post ID {post_id} to channel {TELEGRAM_CHANNEL_ID} successfully!")
        except Exception as e:
            bot.reply_to(message, f"Failed to rebroadcast: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    if bot:
        print("Telegram Bot is active...")
        # This script can be run as a standalone bot or called by Norra.py for broadcasts
        bot.polling()
    else:
        print("Telegram Bot is inactive due to missing token.")

