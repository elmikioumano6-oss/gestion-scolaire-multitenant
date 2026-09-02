import streamlit as st

# Constantes des rôles alignées avec main.py et gestion_utilisateurs.py
ROLE_ADMIN = "admin"
ROLE_PROF = "prof"
ROLE_PARENT = "parent"

# MATRICE D'ACCÈS RBAC harmonisée
ACCESS_MATRIX = {
    # Tous les accès pour l'administrateur
    "Accueil": [ROLE_ADMIN],
    "Année scolaire": [ROLE_ADMIN],
    "Classes & Tarifs": [ROLE_ADMIN],
    "Matières & Coeffs": [ROLE_ADMIN],
    "Enseignants": [ROLE_ADMIN],
    "Personnels et rôles": [ROLE_ADMIN],
    "Gestion Comptes": [ROLE_ADMIN],
    "Inscription Élèves": [ROLE_ADMIN],
    "Import Photos en Masse": [ROLE_ADMIN],
    "Cartes Scolaires": [ROLE_ADMIN],
    "Consultations des notes": [ROLE_ADMIN],
    "Conseil de classe": [ROLE_ADMIN],
    "Bulletins": [ROLE_ADMIN],
    "Supervision cahier": [ROLE_ADMIN],
    "Import Programmes PDF": [ROLE_ADMIN],
    "Suivi des Programmes": [ROLE_ADMIN],
    "Emploi du temps": [ROLE_ADMIN],
    "Planification des évaluations": [ROLE_ADMIN],
    "Encaissement": [ROLE_ADMIN],
    "Stats Encaissements": [ROLE_ADMIN],
    "Soldes & Impayés": [ROLE_ADMIN],
    "Tableau Finances": [ROLE_ADMIN],
    "Dépenses": [ROLE_ADMIN],
    "Rapports": [ROLE_ADMIN],
    "Journal d'activité": [ROLE_ADMIN],
    "Messages": [ROLE_ADMIN],
    "Tableau de bord": [ROLE_ADMIN],
    "Alerte Pédagogique": [ROLE_ADMIN],
    "Sauvegarde & BD": [ROLE_ADMIN],

    # Espace Prof
    "Saisie de notes": [ROLE_ADMIN, ROLE_PROF],
    "Présence": [ROLE_ADMIN, ROLE_PROF],
    "Cahier de texte": [ROLE_ADMIN, ROLE_PROF],

    # Espace Parent
    "Mon Enfant": [ROLE_ADMIN, ROLE_PARENT]
}

def get_user_role():
    return st.session_state.get("user_role", None)

def has_access(module_name: str) -> bool:
    """Vérifie silencieusement si l'utilisateur possède l'accès"""
    user_role = get_user_role()
    if not user_role:
        return False
    return user_role in ACCESS_MATRIX.get(module_name, [])

def require_access(module_name: str):
    """Bloque fermement l'exécution de la page si l'accès est refusé"""
    if not has_access(module_name):
        st.error(f"⛔ ACCÈS REFUSÉ : Votre rôle '{get_user_role()}' ne vous autorise pas à accéder au module '{module_name}'.")
        st.stop()