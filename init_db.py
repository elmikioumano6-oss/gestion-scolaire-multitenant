from database.db_config import SessionLocal, engine, Base
from database.models import User

# Création des tables en base de données si elles n'existent pas
Base.metadata.create_all(bind=engine)

def initialiser_comptes_defaut():
    db = SessionLocal()
    try:
        # Liste des comptes de base à injecter pour la production / test
        comptes_initiaux = [
            {"username": "admin", "password": "adminpassword123", "role": "admin"},
            {"username": "inspecteur", "password": "inspectpassword123", "role": "inspecteur"},
            {"username": "enseignant", "password": "enspassword123", "role": "enseignant"},
            {"username": "parent", "password": "parentpassword123", "role": "parent"}
        ]

        for data in comptes_initiaux:
            # Vérifier si le compte existe déjà pour éviter les doublons
            existe = db.query(User).filter(User.username == data["username"]).first()
            if not existe:
                nouveau_user = User(
                    username=data["username"],
                    password=data["password"], # Pour l'instant en clair, ou stocké tel quel pour correspondre à votre modèle
                    role=data["role"]
                )
                db.add(nouveau_user)
                print(f"Compte créé avec succès : {data['username']} (Rôle : {data['role']})")
            else:
                print(f"Le compte {data['username']} existe déjà en base.")

        db.commit()
        print("Initialisation des comptes terminée avec succès !")
    except Exception as e:
        db.rollback()
        print(f"Erreur lors de l'initialisation : {e}")
    finally:
        db.close()

if __name__ == "__main__":
    initialiser_comptes_defaut()