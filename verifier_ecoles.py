from database.db_config import SessionLocal
from database.models import School

db = SessionLocal()
try:
    ecoles = db.query(School).all()
    for e in ecoles:
        print("--- ÉCOLE ---")
        print(e.__dict__)  # Affiche tous les attributs et colonnes chargés en mémoire
finally:
    db.close()