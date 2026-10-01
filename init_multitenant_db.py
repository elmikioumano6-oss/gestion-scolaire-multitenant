import os
from database.db_config import Base, engine, SessionLocal
from database.models import School, User, AnneeScolaire
import bcrypt
from sqlalchemy import text

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def init_database():
    print("=== Nettoyage et recréation de la base de données multi-tenant ===")
    
    # Suppression propre des tables en ignorant les contraintes circulaires (Cascade)
    with engine.connect() as connection:
        connection.execute(text("DROP TABLE IF EXISTS notes, paiements, presences, eleves, users, classes, matieres, programmes, enseignants, affectations, emplois_du_temps, cahiers_texte, echeances_paiements, planification_evaluations, log_activites, annees_scolaires, schools CASCADE;"))
        connection.commit()

    # Recréation de toutes les tables avec la nouvelle structure
    Base.metadata.create_all(bind=engine)
    print("Tables créées avec succès !")

    db = SessionLocal()
    try:
        # 1. Créer l'école de base
        ecole_rahmat = School(
            nom="CSP Rahmat-FH",
            code="RAHMAT-FH",
            devise="Excellence - Persévérance - Réussite",
            is_active=True
        )
        db.add(ecole_rahmat)
        db.commit()
        db.refresh(ecole_rahmat)
        print(f"École par défaut créée : {ecole_rahmat.nom} (ID: {ecole_rahmat.id})")

        # 2. Créer l'année scolaire active par défaut
        nouvelle_annee = AnneeScolaire(
            school_id=ecole_rahmat.id,
            libelle="2026-2027",
            active=True
        )
        db.add(nouvelle_annee)
        db.commit()
        print("Année scolaire 2026-2027 initialisée.")

        # 3. Créer un Super Administrateur global (accès à toutes les écoles)
        super_admin = User(
            school_id=None,  # Global
            username="superadmin",
            password=hash_password("Admin2026!"),
            role="super_admin"
        )
        db.add(super_admin)
        db.commit()
        print("Compte Super Administrateur créé (username: superadmin / password: Admin2026!)")

        # 4. Créer un administrateur/directeur pour CSP Rahmat-FH
        admin_rahmat = User(
            school_id=ecole_rahmat.id,
            username="admin_rahmat",
            password=hash_password("rahmat2026"),
            role="directeur"
        )
        db.add(admin_rahmat)
        db.commit()
        print("Compte Directeur CSP Rahmat-FH créé (username: admin_rahmat / password: rahmat2026)")

        print("\n=== Initialisation terminée avec succès ! ===")

    except Exception as e:
        db.rollback()
        print(f"Erreur lors de l'initialisation : {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_database()