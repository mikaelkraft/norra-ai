import os
from dotenv import load_dotenv
load_dotenv() # Load environment variables before importing database

from sqlalchemy import text
from database import engine

def migrate():
    print(f"Connecting to database: {engine.url.drivername}...")
    
    statements = [
        "ALTER TABLE match_training_data ADD COLUMN IF NOT EXISTS home_goals INTEGER DEFAULT 0;",
        "ALTER TABLE match_training_data ADD COLUMN IF NOT EXISTS away_goals INTEGER DEFAULT 0;",
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS btts VARCHAR;",
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS dnb VARCHAR;",
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS multi_goals VARCHAR;",
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS ht_ft VARCHAR;",
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS combos VARCHAR;",
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS league_avg_goals FLOAT;",
        """
        CREATE TABLE IF NOT EXISTS post_timeline (
            id SERIAL PRIMARY KEY,
            fixture_id INTEGER,
            platform VARCHAR,
            content VARCHAR,
            link VARCHAR,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """
    ]
    
    # Check if we are running on SQLite (local dry run / test) or PostgreSQL (production)
    is_sqlite = "sqlite" in str(engine.url)
    
    with engine.connect() as conn:
        for stmt in statements:
            # Adjust PostgreSQL dialect specific statements if running on SQLite
            if is_sqlite:
                if "SERIAL PRIMARY KEY" in stmt:
                    stmt = stmt.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                if "TIMESTAMP WITHOUT TIME ZONE" in stmt:
                    stmt = stmt.replace("TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()", "DATETIME DEFAULT CURRENT_TIMESTAMP")
                if "IF NOT EXISTS" in stmt and "ALTER TABLE" in stmt:
                    # SQLite does not support ADD COLUMN IF NOT EXISTS.
                    # We just try to add it, and if it fails because it already exists, we catch and continue.
                    stmt = stmt.replace("IF NOT EXISTS ", "")
            try:
                print(f"Executing: {stmt.strip().splitlines()[0][:60]}...")
                conn.execute(text(stmt))
                conn.commit()
                print("SUCCESS")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column name" in str(e):
                    print("SKIPPED (Column already exists)")
                else:
                    print(f"FAILED: {e}")
                
    print("Database migration completed!")

if __name__ == "__main__":
    migrate()
