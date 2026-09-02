from sqlalchemy import text
from database.db_config import engine

def appliquer_migration():
    requetes = [
        "ALTER TABLE depenses ADD COLUMN IF NOT EXISTS school_id INTEGER;",
        "ALTER TABLE depenses ADD COLUMN IF NOT EXISTS cycle VARCHAR(50);",
        "ALTER TABLE depenses ADD COLUMN IF NOT EXISTS libelle VARCHAR(200);",
        "ALTER TABLE depenses ADD COLUMN IF NOT EXISTS montant FLOAT;",
        "ALTER TABLE depenses ADD COLUMN IF NOT EXISTS categorie VARCHAR(100);",
        "ALTER TABLE depenses ADD COLUMN IF NOT EXISTS date_depense TIMESTAMP;",
        "ALTER TABLE depenses ADD COLUMN IF NOT EXISTS auteur VARCHAR(100);"
    ]
    
    with engine.connect() as conn:
        with conn.begin():
            for req in requetes:
                conn.execute(text(req))
    print("✅ Migration exécutée avec succès !")

if __name__ == "__main__":
    appliquer_migration()