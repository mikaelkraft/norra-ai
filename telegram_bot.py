import os
import telebot
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import database

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def broadcast_predictions():
    """Broadcasts today's top predictions to the Telegram channel."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("Telegram credentials missing in .env")
        return

    db = next(database.get_db())
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

    message += "🔗 [Visit Web Dashboard](https://norra-ai.vercel.app)\n"
    message += "NorraAI Prediction Beacon Force"

    try:
        bot.send_message(TELEGRAM_CHANNEL_ID, message, parse_mode="Markdown")
        print("Telegram broadcast successful!")
    except Exception as e:
        print(f"Telegram broadcast failed: {e}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to Norra AI! Use /today to get latest mathematical forecasts.")

@bot.message_handler(commands=['today'])
def send_predictions(message):
    db = next(database.get_db())
    predictions = db.query(database.Prediction).order_by(database.Prediction.created_at.desc()).limit(5).all()
    
    if not predictions:
        bot.reply_to(message, "No active beacons for today yet.")
        return

    resp = "🎯 **Today's Hot Picks:**\n\n"
    for p in predictions:
        resp += f"⚽ {p.home_team} vs {p.away_team}: {p.prediction_main}\n"
    
    bot.send_message(message.chat.id, resp, parse_mode="Markdown")

if __name__ == "__main__":
    print("Telegram Bot is active...")
    # This script can be run as a standalone bot or called by Norra.py for broadcasts
    bot.polling()
