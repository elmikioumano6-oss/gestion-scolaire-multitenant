import os

class Config:
    APP_NAME = "CSP RAHMAT-FH"
    VERSION = "2.0.0"
    
    # Préparation pour PostgreSQL (par défaut SQLite pour la transition)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///csp_rahmat_v2.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "une_cle_secrete_tres_longue_et_complexe_a_changer_en_prod")
    
    # Paramètres de l'établissement
    ECOLE_NOM = "COMPLEXE SCOLAIRE PRIVE RAHMAT-FH"
    ECOLE_DEVISE = "Excellence - Rigueur - Réussite"
    ECOLE_TELEPHONE = "99797100 / 97327752"
    ECOLE_ADRESSE = "QUARTIER AEROPORT NIAMEY-NIGER"
