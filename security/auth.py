import hashlib
import secrets
import streamlit as st
from datetime import datetime
from database.models import Utilisateur, LogActivite

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return f"{salt}${pwd_hash}"

def verify_password(stored_password: str, provided_password: str) -> bool:
    if '$' not in stored_password:
        return stored_password == provided_password # Rétrocompatibilité
    salt, pwd_hash = stored_password.split('$', 1)
    verify_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return pwd_hash == verify_hash

def authenticate_user(db_session, username, password):
    user = db_session.query(Utilisateur).filter(Utilisateur.username == username, Utilisateur.actif == True).first()
    if user and verify_password(user.password_hash, password):
        # Enregistrement du log de connexion
        log = LogActivite(utilisateur_id=user.id, action="Connexion réussie", module="Authentification")
        db_session.add(log)
        db_session.commit()
        return user
    return None

def login_user(user):
    st.session_state.authenticated = True
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.role = user.role
    st.session_state.nom_complet = user.nom_complet

def logout_user():
    for key in ['authenticated', 'user_id', 'username', 'role', 'nom_complet', 'active_rail', 'nav_module']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.authenticated = False
