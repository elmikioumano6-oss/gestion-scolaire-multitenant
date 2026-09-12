import bcrypt
import streamlit as st
from datetime import datetime
from database.models import User, ActivityLog

def verify_password(stored_password: str, provided_password: str) -> bool:
    try:
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))
    except Exception:
        return False

def authenticate_user(db_session, username, password):
    user = db_session.query(User).filter(User.username == username).first()
    if user and verify_password(user.password, password):
        try:
            log = ActivityLog(user_id=user.id, action="Connexion réussie", module="Authentification")
            db_session.add(log)
            db_session.commit()
        except Exception:
            db_session.rollback()
        return user
    return None

def login_user(user):
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user.id
    st.session_state["username"] = user.username
    st.session_state["role"] = user.role
    st.session_state["school_id"] = user.school_id
    st.session_state["is_super_admin"] = (user.role == "super_admin")

def logout_user():
    keys_to_clear = ['authenticated', 'user_id', 'username', 'role', 'school_id', 'is_super_admin', 'school_name', 'school_code']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["authenticated"] = False