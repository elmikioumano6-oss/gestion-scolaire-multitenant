from database.db_config import engine
from sqlalchemy import text

print("Connexion à la base de données et ajout des colonnes...")

with engine.begin() as conn:
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS salaire_base DOUBLE PRECISION DEFAULT 0.0;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS primes_fixes DOUBLE PRECISION DEFAULT 0.0;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS derniere_activite TIMESTAMP;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS changer_mdp_requis BOOLEAN DEFAULT TRUE;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS enseignant_id INTEGER;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS eleve_id INTEGER;"))

print("Succès ! Les colonnes ont été ajoutées à la table users.")