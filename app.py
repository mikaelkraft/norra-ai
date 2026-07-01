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
    import datetime
    # Fetch 100 recent predictions to categorize
    all_preds = db.query(database.Prediction).order_by(database.Prediction.created_at.desc()).limit(100).all()
    
    now = datetime.datetime.utcnow()
    # 3 hours kickoff grace period. After 3 hours from kickoff, it's considered concluded
    grace_cutoff = now - datetime.timedelta(hours=3)
    
    active_preds = []
    past_preds = []
    
    for p in all_preds:
        # Determine date to check kickoff
        m_date = p.match_date or p.created_at
        
        # If status is pending and match date is either future or within 3h of kickoff, it's active
        if p.status == "pending" and m_date >= grace_cutoff:
            active_preds.append(p)
        else:
            past_preds.append(p)
            
    def format_prediction(p):
        return {
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
            "date": (p.match_date or p.created_at).strftime("%Y-%m-%d %H:%M"),
            "status": p.status,
            "actual_home_goals": p.actual_home_goals,
            "actual_away_goals": p.actual_away_goals
        }
        
    formatted_active = [format_prediction(p) for p in active_preds]
    formatted_past = [format_prediction(p) for p in past_preds]
    
    last_updated = "Unknown"
    if all_preds:
        last_updated = all_preds[0].created_at.strftime("%Y-%m-%d %H:%M UTC")
        
    return {
        "last_updated": last_updated,
        "predictions": formatted_active, # Backward compatibility
        "active_predictions": formatted_active,
        "past_predictions": formatted_past
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

def recalculate_stats(db: Session):
    from Norra import load_bot_stats, update_bot_stats
    import datetime
    try:
        stats = load_bot_stats()
        
        today = datetime.datetime.utcnow()
        # Monday of current week
        start_of_week = today - datetime.timedelta(days=today.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        weekly_wins_count = db.query(database.Prediction).filter(
            database.Prediction.status == "won",
            database.Prediction.created_at >= start_of_week
        ).count()
        
        stats["weekly_wins"] = weekly_wins_count
        update_bot_stats(stats)
        print(f"Stats Recalculated: weekly_wins={weekly_wins_count}")
    except Exception as e:
        print(f"Failed to recalculate weekly wins stats: {e}")

@app.post("/api/admin/decide-outcome")
def decide_outcome(
    fixture_id: int, 
    home_goals: int, 
    away_goals: int, 
    status_override: str, 
    token: str, 
    db: Session = Depends(database.get_db)
):
    secure_token = os.getenv("CRON_TOKEN")
    if not secure_token or token != secure_token:
        raise HTTPException(status_code=401, detail="Unauthorized token.")
        
    pred = db.query(database.Prediction).filter(database.Prediction.fixture_id == fixture_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found.")
        
    pred.actual_home_goals = home_goals
    pred.actual_away_goals = away_goals
    
    if status_override in ["won", "lost", "void"]:
        pred.status = status_override
    else:
        is_correct = False
        p_main = pred.prediction_main.lower()
        h_name = pred.home_team.lower()
        a_name = pred.away_team.lower()
        
        if "draw" in p_main:
            if home_goals == away_goals:
                is_correct = True
        elif h_name in p_main or "home" in p_main:
            if home_goals > away_goals:
                is_correct = True
        elif a_name in p_main or "away" in p_main:
            if away_goals > home_goals:
                is_correct = True
                
        pred.status = "won" if is_correct else "lost"
        
    played = db.query(database.PlayedMatch).filter(database.PlayedMatch.fixture_id == fixture_id).first()
    if not played:
        match_dt = pred.match_date or pred.created_at
        played = database.PlayedMatch(
            fixture_id=fixture_id,
            league_id=None,
            season="2025",
            match_date=match_dt,
            home_team=pred.home_team,
            away_team=pred.away_team,
            home_goals=home_goals,
            away_goals=away_goals
        )
        db.add(played)
    else:
        played.home_goals = home_goals
        played.away_goals = away_goals
        
    db.commit()
    recalculate_stats(db)
    
    return {"status": "success", "prediction_status": pred.status}

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
            .card {{ background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }}
            .btn {{ padding: 10px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: bold; transition: opacity 0.2s; text-decoration: none; display: inline-block; }}
            .btn:hover {{ opacity: 0.9; }}
            .btn-x {{ background: #1da1f2; color: white; }}
            .btn-tg {{ background: #0088cc; color: white; }}
            .btn-cron {{ background: #eab308; color: black; }}
            .btn-save {{ background: #10b981; color: white; }}
            .info {{ display: flex; flex-direction: column; gap: 5px; min-width: 250px; }}
            .teams {{ font-size: 18px; font-weight: bold; }}
            .league {{ font-size: 14px; color: #94a3b8; }}
            .options {{ font-size: 14px; color: #e2e8f0; }}
            .admin-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #334155; padding-bottom: 20px; }}
            
            /* Tabs styling */
            .tabs {{ display: flex; gap: 10px; margin-bottom: 25px; border-bottom: 1px solid #334155; padding-bottom: 10px; }}
            .tab-btn {{ background: transparent; border: 1px solid #475569; color: #94a3b8; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; transition: all 0.2s; }}
            .tab-btn.active, .tab-btn:hover {{ background: #3b82f6; color: white; border-color: #3b82f6; }}
            
            .tab-content {{ display: none; }}
            .tab-content.active {{ display: block; }}
            
            .decider-form {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
            .score-input {{ width: 65px; padding: 8px; border: 1px solid #475569; border-radius: 6px; background: #0f172a; color: white; text-align: center; font-size: 16px; font-weight: bold; }}
            .status-select {{ padding: 8px; background: #0f172a; color: white; border: 1px solid #475569; border-radius: 6px; }}
            .status-badge-inline {{ padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 8px; display: inline-block; }}
            .badge-won {{ background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }}
            .badge-lost {{ background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }}
            .badge-void {{ background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }}
            .badge-pending {{ background: rgba(234, 179, 8, 0.15); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3); }}
        </style>
        <script>
            let predictionsData = {{}};
            
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
            
            async function saveOutcome(fixtureId) {{
                const homeGoals = document.getElementById(`score-home-${{fixtureId}}`).value;
                const awayGoals = document.getElementById(`score-away-${{fixtureId}}`).value;
                const statusOverride = document.getElementById(`override-${{fixtureId}}`).value;
                
                if (homeGoals === "" || awayGoals === "") {{
                    alert("Please input both Home and Away goals.");
                    return;
                }}
                
                const token = "{secure_token}";
                const url = `/api/admin/decide-outcome?fixture_id=${{fixtureId}}&home_goals=${{homeGoals}}&away_goals=${{awayGoals}}&status_override=${{statusOverride}}&token=${{token}}`;
                
                try {{
                    const res = await fetch(url, {{ method: "POST" }});
                    const data = await res.json();
                    if (data.status === "success") {{
                        alert(`Outcome resolved! Status set to: ${{data.prediction_status.toUpperCase()}}`);
                        loadPredictions();
                    }} else {{
                        alert(`Error: ${{data.detail || "Update failed."}}`);
                    }}
                }} catch (err) {{
                    alert(`Network Error: ${{err.message}}`);
                }}
            }}
            
            function switchAdminTab(tabName) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
                
                document.getElementById(`tab-${{tabName}}`).classList.add('active');
                event.target.classList.add('active');
            }}
            
            async function loadPredictions() {{
                const res = await fetch('/predictions');
                const data = await res.json();
                predictionsData = data;
                
                renderActiveList(data.active_predictions || []);
                renderConcludedList(data.past_predictions || []);
            }}
            
            function renderActiveList(activeList) {{
                const container = document.getElementById('active-list-container');
                if (activeList.length === 0) {{
                    container.innerHTML = "<p style='color: #94a3b8;'>No active/pending predictions found today.</p>";
                    return;
                }}
                container.innerHTML = "";
                activeList.forEach(p => {{
                    const card = document.createElement('div');
                    card.className = "card";
                    card.innerHTML = `
                        <div class="info">
                            <div class="teams">${{p.home}} vs ${{p.away}}</div>
                            <div class="league">${{p.league}} | FT: ${{p.main}} (${{p.conf}}) | Avg: ${{p.league_avg_goals || 'N/A'}}</div>
                            <div class="options">Date: ${{p.date}} | DC: ${{p.dc}} | BTTS: ${{p.btts}} | Combo: ${{p.combos}}</div>
                        </div>
                        <div>
                            <button class="btn btn-x" onclick="triggerPost(${{p.fixture_id}}, 'X')">Post to X</button>
                            <button class="btn btn-tg" onclick="triggerPost(${{p.fixture_id}}, 'Telegram')">Post to Telegram</button>
                        </div>
                    `;
                    container.appendChild(card);
                }});
            }}
            
            function renderConcludedList(pastList) {{
                const container = document.getElementById('concluded-list-container');
                if (pastList.length === 0) {{
                    container.innerHTML = "<p style='color: #94a3b8;'>No concluded/archive predictions found in database.</p>";
                    return;
                }}
                container.innerHTML = "";
                pastList.forEach(p => {{
                    const card = document.createElement('div');
                    card.className = "card";
                    
                    const badgeClass = p.status === 'won' ? 'badge-won' : (p.status === 'lost' ? 'badge-lost' : (p.status === 'void' ? 'badge-void' : 'badge-pending'));
                    const statusText = p.status.toUpperCase();
                    
                    card.innerHTML = `
                        <div class="info">
                            <div class="teams">${{p.home}} vs ${{p.away}} <span class="status-badge-inline ${{badgeClass}}">${{statusText}}</span></div>
                            <div class="league">${{p.league}} | Predicted: <strong>${{p.main}}</strong> (${{p.conf}})</div>
                            <div class="options">Date: ${{p.date}} | Current Score: ${{p.actual_home_goals !== null ? `${{p.actual_home_goals}} - ${{p.actual_away_goals}}` : 'None'}}</div>
                        </div>
                        <div class="decider-form">
                            <input type="number" id="score-home-${{p.fixture_id}}" class="score-input" placeholder="Home" value="${{p.actual_home_goals !== null ? p.actual_home_goals : ''}}" min="0" />
                            <span>-</span>
                            <input type="number" id="score-away-${{p.fixture_id}}" class="score-input" placeholder="Away" value="${{p.actual_away_goals !== null ? p.actual_away_goals : ''}}" min="0" />
                            <select id="override-${{p.fixture_id}}" class="status-select">
                                <option value="auto" ${{p.status === 'pending' ? 'selected' : ''}}>Auto Calculate</option>
                                <option value="won" ${{p.status === 'won' ? 'selected' : ''}}>Force Won</option>
                                <option value="lost" ${{p.status === 'lost' ? 'selected' : ''}}>Force Lost</option>
                                <option value="void" ${{p.status === 'void' ? 'selected' : ''}}>Force Void</option>
                            </select>
                            <button class="btn btn-save" onclick="saveOutcome(${{p.fixture_id}})">Resolve</button>
                        </div>
                    `;
                    container.appendChild(card);
                }});
            }}
            
            window.onload = loadPredictions;
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
        
        <div class="tabs">
            <button class="tab-btn active" onclick="switchAdminTab('active')">📡 Active VIP Picks</button>
            <button class="tab-btn" onclick="switchAdminTab('concluded')">⚖️ Resolve Concluded Matches</button>
        </div>
        
        <div id="tab-active" class="tab-content active">
            <div id="active-list-container">
                Loading active predictions...
            </div>
        </div>
        
        <div id="tab-concluded" class="tab-content">
            <div id="concluded-list-container">
                Loading concluded predictions...
            </div>
        </div>
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
            try:
                verify_previous_matches(None)
            except Exception as e:
                print(f"Error in background match verification: {e}")
                
            try:
                # Runs twice daily predictions, filtering and auto-posting only those with confidence > 90%
                fetch_predictions(api_key=None, dry_run=False)
            except Exception as e:
                print(f"Error in background prediction run: {e}")

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
        
    # 2. If not found, safely return a 404 to avoid live API lookup / abuse
    raise HTTPException(
        status_code=404, 
        detail=f"No active predictions found for '{query.capitalize()}' in our database. Predictions are generated daily by our automated system."
    )

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
                
        # If not found in the database, safely inform the user to prevent active API calls/abuse
        searched_teams = ", ".join([w.capitalize() for w in words[:3]])
        return {
            "response": (
                f"I couldn't find any active predictions for '{searched_teams}' in my database right now. "
                "Predictions are generated daily by our automated system. "
                "Please check the main dashboard on the homepage to see today's active fixtures, or check back later when predictions are updated!"
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

