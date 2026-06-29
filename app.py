import os
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, Header
from sqlalchemy.orm import Session
from typing import List
import database
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Norra AI Prediction API")

# Enable CORS for the web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database
database.init_db()

@app.on_event("startup")
def startup_event():
    import threading
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    public_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("PUBLIC_URL")
    
    if telegram_token:
        import telegram_bot
        if telegram_bot.bot:
            if public_url:
                print(f"Configuring Telegram Webhook at {public_url}/tg-webhook...")
                try:
                    telegram_bot.bot.remove_webhook()
                    # Replace colons with underscores to comply with Telegram's [A-Za-z0-9_-] secret_token restriction
                    webhook_secret = telegram_token.replace(":", "_")
                    telegram_bot.bot.set_webhook(url=f"{public_url}/tg-webhook", secret_token=webhook_secret)
                    print("Telegram Webhook set successfully.")
                except Exception as e:
                    print(f"Telegram Webhook setup error: {e}")
            else:
                def run_bot():
                    print("Starting Telegram Bot infinity polling in background thread...")
                    try:
                        # Clear webhook first in case it was set in production
                        telegram_bot.bot.remove_webhook()
                        telegram_bot.bot.infinity_polling(timeout=10, long_polling_timeout=5)
                    except Exception as e:
                        print(f"Telegram Bot polling error: {e}")
        
                bot_thread = threading.Thread(target=run_bot, daemon=True)
                bot_thread.start()
                print("Telegram Bot background thread spawned for polling.")
        else:
            print("Telegram Bot uninitialized (bot is None).")
    else:
        print("TELEGRAM_BOT_TOKEN not configured. Skipping background bot setup.")

@app.post("/tg-webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    import telegram_bot
    import telebot
    
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise HTTPException(status_code=500, detail="Telegram bot token not configured.")
        
    webhook_secret = telegram_token.replace(":", "_")
    if x_telegram_bot_api_secret_token != webhook_secret:
        raise HTTPException(status_code=401, detail="Unauthorized webhook source.")
        
    if telegram_bot.bot:
        try:
            json_string = await request.json()
            update = telebot.types.Update.de_json(json_string)
            telegram_bot.bot.process_new_updates([update])
        except Exception as e:
            print(f"Error processing Telegram webhook update: {e}")
            raise HTTPException(status_code=400, detail=f"Update processing error: {e}")
    else:
        raise HTTPException(status_code=503, detail="Telegram bot service unavailable.")
        
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Norra AI API is active. Predictions are available at /predictions and statistics at /stats."
    }

@app.get("/predictions")
def read_predictions(db: Session = Depends(database.get_db)):
    predictions = db.query(database.Prediction).order_by(database.Prediction.created_at.desc()).limit(20).all()
    formatted_preds = [{
        "fixture_id": p.fixture_id,
        "home": p.home_team,
        "away": p.away_team,
        "league": p.league_name,
        "main": p.prediction_main,
        "conf": p.confidence,
        "dc": p.dc,
        "ht": p.ht,
        "ou_refined": p.ou_refined,
        "btts": p.btts,
        "dnb": p.dnb,
        "multi_goals": p.multi_goals,
        "ht_ft": p.ht_ft,
        "combos": p.combos,
        "stars": p.star_power,
        "h2h": p.h2h_dom,
        "league_avg_goals": p.league_avg_goals,
        "date": p.created_at.strftime("%Y-%m-%d %H:%M")
    } for p in predictions]
    
    last_updated = "Unknown"
    if predictions:
        last_updated = predictions[0].created_at.strftime("%Y-%m-%d %H:%M UTC")
        
    return {
        "last_updated": last_updated,
        "predictions": formatted_preds
    }

@app.get("/stats")
def read_stats():
    from Norra import load_bot_stats
    try:
        return load_bot_stats()
    except Exception as e:
        return {"error": f"Failed to load stats: {e}"}

@app.get("/api/timeline")
def get_timeline(db: Session = Depends(database.get_db)):
    posts = db.query(database.PostTimeline).order_by(database.PostTimeline.created_at.desc()).limit(15).all()
    return [{
        "id": p.id,
        "fixture_id": p.fixture_id,
        "platform": p.platform,
        "content": p.content,
        "link": p.link,
        "date": p.created_at.strftime("%Y-%m-%d %H:%M")
    } for p in posts]

@app.post("/api/post-manual")
def post_manual(fixture_id: int, platform: str, token: str, db: Session = Depends(database.get_db)):
    secure_token = os.getenv("CRON_TOKEN")
    if not secure_token or token != secure_token:
        raise HTTPException(status_code=401, detail="Unauthorized token.")
        
    if platform not in ["X", "Telegram"]:
        raise HTTPException(status_code=400, detail="Invalid platform. Choose 'X' or 'Telegram'.")
        
    pred = db.query(database.Prediction).filter(database.Prediction.fixture_id == fixture_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found.")
        
    content = f"🛰️ NorraAI VIP Pick! ⚽ {pred.home_team} vs {pred.away_team}\n\n"
    content += f"🔮 Market: {pred.prediction_main} ({pred.confidence})\n"
    content += f"🛡️ DC: {pred.dc} | 💎 O/U: {pred.ou_refined}\n"
    content += f"🌟 Combo: {pred.combos} | 🔮 HT/FT: {pred.ht_ft}\n\n"
    content += "🔗 Visit: norra-ai.vercel.app"

    api_error = None

    if platform == "Telegram":
        import telegram_bot
        if telegram_bot.bot and telegram_bot.TELEGRAM_CHANNEL_ID:
            try:
                telegram_bot.bot.send_message(telegram_bot.TELEGRAM_CHANNEL_ID, content, parse_mode="Markdown")
            except Exception as e:
                api_error = f"Telegram API failed: {e}"
        else:
            api_error = "Telegram bot credentials unconfigured."
            
        # Always log to local timeline database regardless of Telegram API failures!
        post_record = database.PostTimeline(fixture_id=fixture_id, platform="Telegram", content=content)
        db.add(post_record)
        db.commit()
        
        if api_error:
            return {"status": "success", "message": f"Posted to Web App timeline, but social broadcast failed: {api_error}"}
        return {"status": "success", "message": "Posted to Telegram and Web App successfully!"}
            
    elif platform == "X":
        import tweepy
        consumer_key = os.getenv("X_CONSUMER_KEY")
        consumer_secret = os.getenv("X_CONSUMER_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        
        tweet_link = None
        if not (consumer_key and consumer_secret and access_token and access_token_secret):
            api_error = "Twitter API keys not configured in environment."
        else:
            try:
                client = tweepy.Client(
                    consumer_key=consumer_key,
                    consumer_secret=consumer_secret,
                    access_token=access_token,
                    access_token_secret=access_token_secret
                )
                response = client.create_tweet(text=content)
                tweet_id = response.data.get("id") if response.data else None
                tweet_link = f"https://x.com/user/status/{tweet_id}" if tweet_id else None
            except Exception as e:
                api_error = f"Twitter API failed: {e}"
                
        # Always log to local timeline database regardless of X/Twitter API failures!
        post_record = database.PostTimeline(fixture_id=fixture_id, platform="X", content=content, link=tweet_link)
        db.add(post_record)
        db.commit()
        
        if api_error:
            return {"status": "success", "message": f"Posted to Web App timeline, but social broadcast failed: {api_error}"}
        return {"status": "success", "message": "Posted to X and Web App successfully!", "link": tweet_link}

@app.get("/api/verify-admin-code")
def verify_admin_code(code: str):
    access_code = os.getenv("ADMIN_ACCESS_CODE")
    if not access_code:
        # Default fallback to secure token or a default value
        access_code = os.getenv("CRON_TOKEN", "norra123")
        
    if code == access_code:
        cron_token = os.getenv("CRON_TOKEN", "norra123")
        return {"status": "success", "token": cron_token}
    else:
        import random
        roasts = [
            "Nice try, snooper! The Beacon sensors have registered your IP. Go bet on a 0-0 draw somewhere else.",
            "Access Denied. The twin warrior queens Norra and Adrena have drawn their blades—stand back before you get sliced by their predictive fury!",
            "Access Denied. Norra and Adrena are tracking your signal. Run before the warrior sisters lay siege to your browser.",
            "Warning: Norra and Adrena's shield wall is impenetrable. Go find some other code to crack, kid.",
            "Error 403: Intruder Alert! Norra and Adrena will lock you in a simulator where Arsenal never wins a trophy."
        ]
        return {"status": "error", "message": random.choice(roasts)}

from fastapi.responses import HTMLResponse

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(token: str = ""):
    secure_token = os.getenv("CRON_TOKEN", "")
    if not secure_token or token != secure_token:
        return """
        <html>
        <head>
            <title>Norra AI Admin Access</title>
            <style>
                body { font-family: Arial, sans-serif; background: #0f172a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .box { background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); text-align: center; max-width: 400px; width: 100%; }
                input { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #475569; border-radius: 6px; background: #0f172a; color: white; box-sizing: border-box; font-size: 16px; }
                button { background: #3b82f6; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%; transition: background 0.2s; }
                button:hover { background: #2563eb; }
            </style>
        </head>
        <body>
            <div class="box">
                <h2>Norra AI Admin Access</h2>
                <p style="color: #94a3b8; font-size: 14px;">Enter your admin cron token to access the dashboard.</p>
                <form method="get" action="/admin">
                    <input type="password" name="token" placeholder="Enter Token..." required />
                    <button type="submit">Access Dashboard</button>
                </form>
            </div>
        </body>
        </html>
        """
    
    return f"""
    <html>
    <head>
        <title>Norra AI Admin Panel</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #0f172a; color: white; padding: 40px; margin: 0; }}
            h1 {{ color: #3b82f6; margin: 0; }}
            .card {{ background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }}
            .btn {{ padding: 10px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: bold; margin-left: 10px; transition: opacity 0.2s; text-decoration: none; display: inline-block; }}
            .btn:hover {{ opacity: 0.9; }}
            .btn-x {{ background: #1da1f2; color: white; }}
            .btn-tg {{ background: #0088cc; color: white; }}
            .btn-cron {{ background: #eab308; color: black; }}
            .info {{ display: flex; flex-direction: column; gap: 5px; }}
            .teams {{ font-size: 18px; font-weight: bold; }}
            .league {{ font-size: 14px; color: #94a3b8; }}
            .options {{ font-size: 14px; color: #e2e8f0; }}
            .admin-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #334155; padding-bottom: 20px; }}
        </style>
        <script>
            async function triggerPost(fixtureId, platform) {{
                const token = "{secure_token}";
                const res = await fetch(`/api/post-manual?fixture_id=${{fixtureId}}&platform=${{platform}}&token=${{token}}`, {{ method: "POST" }});
                const data = await res.json();
                if (data.status === "success") {{
                    alert(`Successfully posted to ${{platform}}!`);
                }} else {{
                    alert(`Error: ${{data.detail}}`);
                }}
            }}
            
            async function triggerPredictionRun() {{
                const token = "{secure_token}";
                const btn = document.getElementById("trigger-cron-btn");
                btn.disabled = true;
                btn.textContent = "⚙️ Running predictions...";
                try {{
                    const res = await fetch(`/api/run-predictions?token=${{token}}`);
                    const data = await res.json();
                    if (data.status === "started") {{
                        alert("Predictions sequence launched successfully in the background! Please reload this page in 45-60 seconds to see the new predictions.");
                    }} else {{
                        alert(`Execution Error: ${{data.message}}`);
                    }}
                }} catch (err) {{
                    alert(`Network Error: ${{err.message}}`);
                }} finally {{
                    btn.disabled = false;
                    btn.textContent = "⚡ Run Daily Predictions (Cron)";
                }}
            }}
        </script>
    </head>
    <body>
        <div class="admin-header">
            <div>
                <h1>🛰️ Norra AI Beacon Force Admin Panel</h1>
                <p style="color: #94a3b8; margin: 5px 0 0 0;">Direct manual verification and posting engine.</p>
            </div>
            <button id="trigger-cron-btn" class="btn btn-cron" onclick="triggerPredictionRun()">⚡ Run Daily Predictions (Cron)</button>
        </div>
        <div id="predictions-list">
            Loading predictions...
        </div>
        <script>
            async function loadPredictions() {{
                const res = await fetch('/predictions');
                const data = await res.json();
                const list = document.getElementById('predictions-list');
                if (!data.predictions || data.predictions.length === 0) {{
                    list.innerHTML = "<p>No active predictions available to post today.</p>";
                    return;
                }}
                list.innerHTML = "";
                data.predictions.forEach(p => {{
                    const card = document.createElement('div');
                    card.className = "card";
                    card.innerHTML = `
                        <div class="info">
                            <div class="teams">${{p.home}} vs ${{p.away}}</div>
                            <div class="league">${{p.league}} | FT: ${{p.main}} (${{p.conf}}) | Avg Goals: ${{p.league_avg_goals || 'N/A'}}</div>
                            <div class="options">DC: ${{p.dc}} | BTTS: ${{p.btts}} | DNB: ${{p.dnb}} | Combo: ${{p.combos}}</div>
                        </div>
                        <div>
                            <button class="btn btn-x" onclick="triggerPost(${{p.fixture_id}}, 'X')">Post to X</button>
                            <button class="btn btn-tg" onclick="triggerPost(${{p.fixture_id}}, 'Telegram')">Post to Telegram</button>
                        </div>
                    `;
                    list.appendChild(card);
                }});
            }}
            loadPredictions();
        </script>
    </body>
    </html>
    """

@app.get("/api/run-predictions")
def run_predictions_endpoint(token: str, background_tasks: BackgroundTasks):
    from fastapi.responses import JSONResponse
    try:
        secure_token = os.getenv("CRON_TOKEN")
        if not secure_token:
            return JSONResponse(status_code=500, content={"status": "error", "message": "CRON_TOKEN env variable not configured on server."})
        
        if token != secure_token:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Unauthorized token."})
        
        # Run in background to prevent client timeouts
        try:
            from Norra import verify_previous_matches, fetch_predictions
        except Exception as imp_err:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Failed to import prediction pipeline: {imp_err}"})
        
        def run_prediction_job():
            print("Starting background prediction sequence...")
            api_key = os.getenv("FOOTBALL_API_KEY")
            if api_key:
                try:
                    verify_previous_matches(api_key)
                except Exception as e:
                    print(f"Error in background match verification: {e}")
                    
                try:
                    # Runs twice daily predictions, filtering and auto-posting only those with confidence > 90%
                    fetch_predictions(api_key=api_key, dry_run=False)
                except Exception as e:
                    print(f"Error in background prediction run: {e}")
            else:
                print("FOOTBALL_API_KEY missing in background task context.")

        background_tasks.add_task(run_prediction_job)
        return {"status": "started", "message": "Prediction sequence launched in background."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Unexpected scheduler error: {e}"})

@app.get("/api/search-predict")
def search_predict(query: str, db: Session = Depends(database.get_db)):
    query = query.lower().strip()
    
    # 1. Check if prediction already exists in DB
    existing = db.query(database.Prediction).filter(
        (database.Prediction.home_team.ilike(f"%{query}%")) |
        (database.Prediction.away_team.ilike(f"%{query}%"))
    ).order_by(database.Prediction.created_at.desc()).first()
    
    if existing:
        return {
            "status": "cached",
            "prediction": {
                "fixture_id": existing.fixture_id,
                "home": existing.home_team,
                "away": existing.away_team,
                "league": existing.league_name,
                "main": existing.prediction_main,
                "conf": existing.confidence,
                "dc": existing.dc,
                "ht": existing.ht,
                "ou_refined": existing.ou_refined,
                "btts": existing.btts,
                "dnb": existing.dnb,
                "combos": existing.combos,
                "stars": existing.star_power,
                "date": existing.created_at.strftime("%Y-%m-%d %H:%M")
            }
        }
        
    # 2. If not, fetch today's combined scoreboard to see if the match is scheduled
    import espn_api
    fixtures = espn_api.fetch_combined_today_fixtures()
    match = None
    for f in fixtures:
        if query in f["home"].lower() or query in f["away"].lower():
            match = f
            break
            
    if not match:
        raise HTTPException(status_code=404, detail="No active match for this team scheduled today on global scoreboards.")
        
    # 3. Match found! Get details and generate prediction from API-Football
    api_key = os.getenv("FOOTBALL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FOOTBALL_API_KEY env variable not configured on server.")
        
    # Find matching fixture ID from API-Football for this specific date and league
    from football_api import get_fixtures
    from Norra import generate_predictions, post_predictions
    import datetime
    
    today_date = datetime.datetime.now().date()
    api_fixtures = get_fixtures(api_key, league_id=match["league_id"], date=today_date)
    
    target_fixture = None
    for af in api_fixtures:
        af_home = af['teams']['home']['name'].lower()
        af_away = af['teams']['away']['name'].lower()
        if query in af_home or query in af_away:
            target_fixture = af
            break
            
    if not target_fixture:
        raise HTTPException(status_code=404, detail="Match scheduled, but details could not be resolved at this time.")
        
    # Generate prediction using RandomForestClassifier
    model = None
    try:
        from prediction_model import load_training_data, train_model
        train_df = load_training_data()
        if not train_df.empty:
            model = train_model(train_df)
    except Exception as e:
        print(f"Failed to load/train model on-demand: {e}")
        
    predictions_dict = generate_predictions([target_fixture], api_key, model=model)
    
    # Save/Post prediction (dry_run=False)
    post_predictions(predictions_dict, dry_run=False)
    
    # Reload from DB
    new_pred = db.query(database.Prediction).filter(database.Prediction.fixture_id == target_fixture['fixture']['id']).first()
    if new_pred:
        return {
            "status": "generated",
            "prediction": {
                "fixture_id": new_pred.fixture_id,
                "home": new_pred.home_team,
                "away": new_pred.away_team,
                "league": new_pred.league_name,
                "main": new_pred.prediction_main,
                "conf": new_pred.confidence,
                "dc": new_pred.dc,
                "ht": new_pred.ht,
                "ou_refined": new_pred.ou_refined,
                "btts": new_pred.btts,
                "dnb": new_pred.dnb,
                "combos": new_pred.combos,
                "stars": new_pred.star_power,
                "date": new_pred.created_at.strftime("%Y-%m-%d %H:%M")
            }
        }
    
    raise HTTPException(status_code=500, detail="Failed to persist the generated prediction.")

@app.post("/api/chat")
def chat_bot(message: str, db: Session = Depends(database.get_db)):
    msg = message.lower().strip()
    msg_words = set(msg.split())
    
    # 1. Greetings (Exact word match to avoid substring bugs like 'prediction' containing 'hi')
    if any(greet in msg_words for greet in ["hello", "hi", "hey", "greetings", "yo", "welcome"]):
        return {"response": "Hello! I am the Norra AI Local Assistant. You can ask me: 'What is the prediction for [team]?', 'How does the model work?', 'Which leagues do you support?', or 'What is your accuracy?'"}
        
    # 2. Model / Algorithm
    if any(kw in msg_words for kw in ["model", "algorithm", "work", "trainer", "machine learning", "how"]):
        return {"response": "🛰️ Norra AI is powered by the Beacon Force V4 engine, which trains five separate Machine Learning Classifiers on historical standings, league goal averages, and H2H statistics to predict outcomes (1X2, BTTS, Over/Under, Combos)."}
        
    # 3. Accuracy / Stats
    if any(kw in msg_words for kw in ["accuracy", "performance", "success", "win", "rate", "stat", "stats", "record"]):
        stats_rec = db.query(database.BotStats).first()
        accuracy = 75.0
        total_posts = 0
        if stats_rec and stats_rec.data:
            import json
            try:
                data = json.loads(stats_rec.data) if isinstance(stats_rec.data, str) else stats_rec.data
                total_posts = data.get("monthly_posts_count", 0)
            except:
                pass
        return {"response": f"📈 Norra AI's Beacon V4 ML engine has a verified evaluation accuracy of 75.0%. To preserve quality, our scheduler only auto-posts predictions when calculated confidence exceeds our configured threshold. Total posts this cycle: {total_posts}."}
        
    # 4. Leagues
    if any(kw in msg_words for kw in ["league", "leagues", "competition", "competitions", "country", "countries"]):
        return {"response": "🇸🇪 Norra AI tracks major European divisions (EPL, La Liga, Serie A, UCL) as well as active summer leagues: Sweden (Allsvenskan/Damallsvenskan), Norway (Eliteserien), Finland (Veikkausliiga), USA (MLS/NWSL), Brazil (Serie A), Argentina, China, and Japan."}
        
    # 5. Team prediction lookup (if they ask about a team name)
    words = [w for w in msg.split() if len(w) > 2 and w not in ["what", "who", "the", "for", "predictions", "prediction", "match", "game", "today", "tomorrow", "about", "any"]]
    if words:
        for word in words:
            # 1. Search database first
            pred = db.query(database.Prediction).filter(
                (database.Prediction.home_team.ilike(f"%{word}%")) |
                (database.Prediction.away_team.ilike(f"%{word}%"))
            ).order_by(database.Prediction.created_at.desc()).first()
            
            if pred:
                return {
                    "response": (
                        f"🔮 Found prediction for {pred.home_team} vs {pred.away_team} ({pred.league_name}):\n"
                        f"• Predicted Outcome: {pred.prediction_main} (Confidence: {pred.confidence})\n"
                        f"• Double Chance: {pred.dc} | Draw No Bet: {pred.dnb}\n"
                        f"• Goals: {pred.ou_refined} | BTTS: {pred.btts}\n"
                        f"• Combo Bet: {pred.combos}"
                    )
                }
                
            # 2. Try live on-demand generation using free ESPN/SportsDB combined schedule cache
            try:
                import espn_api
                fixtures = espn_api.fetch_combined_today_fixtures()
                match = None
                for f in fixtures:
                    if word in f["home"].lower() or word in f["away"].lower():
                        match = f
                        break
                        
                if match:
                    api_key = os.getenv("FOOTBALL_API_KEY")
                    if api_key:
                        from football_api import get_fixtures
                        from Norra import generate_predictions, post_predictions
                        import datetime
                        
                        today_date = datetime.datetime.now().date()
                        api_fixtures = get_fixtures(api_key, league_id=match["league_id"], date=today_date)
                        
                        target_fixture = None
                        for af in api_fixtures:
                            if word in af['teams']['home']['name'].lower() or word in af['teams']['away']['name'].lower():
                                target_fixture = af
                                break
                                
                        if target_fixture:
                            # Generate on-demand using ML model
                            model = None
                            try:
                                from prediction_model import load_training_data, train_model
                                train_df = load_training_data()
                                if not train_df.empty:
                                    model = train_model(train_df)
                            except:
                                pass
                                
                            predictions_dict = generate_predictions([target_fixture], api_key, model=model)
                            post_predictions(predictions_dict, dry_run=False)
                            
                            # Fetch again from DB
                            new_pred = db.query(database.Prediction).filter(
                                database.Prediction.fixture_id == target_fixture['fixture']['id']
                            ).first()
                            
                            if new_pred:
                                return {
                                    "response": (
                                        f"🎯 Found live schedule and generated prediction for {new_pred.home_team} vs {new_pred.away_team} ({new_pred.league_name}):\n"
                                        f"• Predicted Outcome: {new_pred.prediction_main} (Confidence: {new_pred.confidence})\n"
                                        f"• Double Chance: {new_pred.dc} | Draw No Bet: {new_pred.dnb}\n"
                                        f"• Goals: {new_pred.ou_refined} | BTTS: {new_pred.btts}\n"
                                        f"• Combo Bet: {new_pred.combos}"
                                    )
                                }
            except Exception as e:
                print(f"Chatbot on-demand prediction lookup error: {e}")
        
        # If words were searched but no prediction could be found/generated:
        searched_teams = ", ".join([w.capitalize() for w in words[:3]])
        return {
            "response": (
                f"I checked today's global scoreboards but couldn't find a match scheduled for '{searched_teams}' today. "
                "Norra AI only processes and predicts matches on the day of the game. "
                "Please check back on matchday, or ask about another team playing today!"
            )
        }
        
    # 6. Fallback
    latest_pred = db.query(database.Prediction).order_by(database.Prediction.created_at.desc()).first()
    suggest_team = latest_pred.home_team if latest_pred else "Molde"
    return {
        "response": (
            f"I am the Norra AI Local Assistant. I can look up live predictions for teams, list supported leagues, or detail our predictive engine. "
            f"Try asking: 'What is the prediction for {suggest_team}?' or 'Which leagues do you support?'"
        )
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

