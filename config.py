import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    APP_NAME = "CSP RAHMAT-FH"
    VERSION = "2.0.0"
    
    # Configuration PostgreSQL via le tunnel SSH local
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://erp_user:Rahmatfh2026@127.0.0.1:5432/school_erp")
    SECRET_KEY = os.getenv("SECRET_KEY", "une_cle_secrete_tres_longue_et_complexe_a_changer_en_prod")
    
    # Paramètres de l'établissement
    ECOLE_NOM = "COMPLEXE SCOLAIRE PRIVE RAHMAT-FH"
    ECOLE_DEVISE = "Excellence - Rigueur - Réussite"
    ECOLE_TELEPHONE = "99797100 / 97327752"
    ECOLE_ADRESSE = "QUARTIER AEROPORT NIAMEY-NIGER"