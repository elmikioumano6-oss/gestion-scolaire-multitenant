from sqlalchemy import text
from database.db_config import engine

with engine.connect() as connection:
    try:
        connection.execute(text("ALTER TABLE schools ADD COLUMN IF NOT EXISTS actif BOOLEAN DEFAULT TRUE;"))
        connection.commit()
        print("✅ Colonne 'actif' vérifiée/ajoutée avec succès sur Supabase.")
    except Exception as e:
        print(f"Erreur actif : {e}")

    try:
        connection.execute(text("ALTER TABLE schools ADD COLUMN IF NOT EXISTS date_expiration TIMESTAMP;"))
        connection.commit()
        print("✅ Colonne 'date_expiration' vérifiée/ajoutée avec succès sur Supabase.")
    except Exception as e:
        print(f"Erreur date_expiration : {e}")