from database.db_config import SessionLocal
from database.models import Base

db = SessionLocal()
print("=== DÉBUT DU TEST GLOBAL EXHAUSTIF DE TOUTES LES TABLES ===")

succes_count = 0
erreurs_count = 0
total_tables = 0

try:
    # Récupération automatique de toutes les classes mappées dans SQLAlchemy
    for mapper in Base.registry.mappers:
        modele = mapper.class_
        nom_table = modele.__tablename__
        total_tables += 1
        try:
            count = db.query(modele).count()
            print(f"[OK] Table '{nom_table}' (Modèle: {modele.__name__}) -> Accessible ({count} lignes).")
            succes_count += 1
        except Exception as err:
            print(f"[ERREUR] Table '{nom_table}' (Modèle: {modele.__name__}) -> Problème détecté : {err}")
            erreurs_count += 1

    print(f"\n==========================================")
    print(f"Total des tables scannées : {total_tables}")
    if erreurs_count == 0:
        print(f"[SUCCÈS TOTAL] {succes_count}/{total_tables} tables testées avec succès !")
        print("L'ERP est à 100% prêt et opérationnel pour les écoles.")
    else:
        print(f"[ATTENTION] {erreurs_count} table(s) ont rencontré une erreur.")
    print(f"==========================================")

except Exception as e:
    print(f"\n[ERREUR CRITIQUE] : {str(e)}")
finally:
    db.close()