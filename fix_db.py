from database.db_config import engine
from sqlalchemy import text

with engine.connect() as connection:
    connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS changer_mdp_requis BOOLEAN DEFAULT FALSE;"))
    connection.commit()
print("Colonne ajoutée avec succès !")