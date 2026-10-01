from datetime import datetime, timedelta
from database.db_config import SessionLocal
from database.models import School, User

def clean_expired_tenants():
    db = SessionLocal()
    try:
        # Par exemple, suppression automatique 30 jours après l'expiration de l'essai
        delai_grace = 30 
        date_limite = datetime.now() - timedelta(days=delai_grace)

        # Trouver les écoles en période d'essai expirées avant la date limite
        ecoles_a_supprimer = db.query(School).filter(
            School.is_trial == True,
            School.trial_expires_at < date_limite
        ).all()

        for ecole in ecoles_a_supprimer:
            print(f"Suppression de l'école expirée : {ecole.nom} (ID: {ecole.id})")
            # Si vos clés étrangères sont en cascade, supprimer l'école supprime tout le reste
            db.delete(ecole)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erreur lors du nettoyage automatique : {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_expired_tenants()