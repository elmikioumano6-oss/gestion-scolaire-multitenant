from database.db_config import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE matieres ADD COLUMN IF NOT EXISTS volume_horaire FLOAT DEFAULT 0.0;"))
    conn.commit()
print("✅ Colonne 'volume_horaire' ajoutée avec succès à la table 'matieres' !")