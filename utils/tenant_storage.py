import os
import streamlit as st

def get_tenant_upload_dir():
    """Retourne et crée dynamiquement le dossier d'upload spécifique au tenant actif."""
    subdomain = "default"
    
    # 1. Extraction dynamique depuis l'en-tête Host de la requête
    try:
        host = st.context.headers.get("Host", "") or st.context.headers.get("X-Forwarded-Host", "")
        if host and "localhost" not in host and "127.0.0.1" not in host:
            parts = host.split(".")
            if len(parts) > 2:
                subdomain = parts[0].lower()
    except Exception:
        pass
    
    # 2. Fallback dynamique basé sur le nom de l'école stocké en session (quel qu'il soit)
    if subdomain == "default":
        school_name = st.session_state.get("school_name", "")
        if school_name:
            subdomain = "".join(c if c.isalnum() else "_" for c in school_name.lower()).strip("_")

    upload_dir = os.path.join("uploads", subdomain)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir