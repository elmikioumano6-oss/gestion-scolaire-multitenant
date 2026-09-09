from database.db_config import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE schools ADD COLUMN IF NOT EXISTS subdomain VARCHAR(100) UNIQUE;"))
    db.execute(text("ALTER TABLE schools ADD COLUMN IF NOT EXISTS is_trial BOOLEAN DEFAULT FALSE;"))
    db.execute(text("ALTER TABLE schools ADD COLUMN IF NOT EXISTS trial_expires_at TIMESTAMP;"))
    db.commit()
    print("Migration réussie !")
except Exception as e:
    db.rollback()
    print(f"Erreur : {e}")
finally:
    db.close()