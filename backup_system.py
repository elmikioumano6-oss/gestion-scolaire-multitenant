import shutil
import os
from datetime import datetime

def perform_backup():
    # Définition des dossiers
    dossier_projet = os.path.dirname(os.path.abspath(__file__))
    dossier_backup = os.path.join(dossier_projet, "backups")
    fichier_db = os.path.join(dossier_projet, "csp_rahmat_v2.db")
    
    # Création du dossier backups s'il n'existe pas
    if not os.path.exists(dossier_backup):
        os.makedirs(dossier_backup)
        
    # Création du nom de fichier daté
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nom_backup = f"backup_csp_{date_str}.db"
    destination = os.path.join(dossier_backup, nom_backup)
    
    # Sauvegarde
    if os.path.exists(fichier_db):
        shutil.copy2(fichier_db, destination)
        print(f"✅ Sauvegarde réussie : {nom_backup} dans le dossier /backups")
    else:
        print("❌ Erreur : Le fichier de base de données est introuvable.")

if __name__ == "__main__":
    perform_backup()