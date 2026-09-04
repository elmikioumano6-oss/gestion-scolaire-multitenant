import streamlit as st
from datetime import datetime
from database.db_config import SessionLocal
from database.models import JournalActivite, SystemLog
import traceback

def log_action_erp(module, action, statut="Succès", valeur_avant=None, valeur_apres=None):
    """
    Enregistre une action sensible avec traçabilité granulaire (Normes ERP - SOC 2 / ISO 27001).
    Capture l'utilisateur connecté, l'école active, l'IP, la session et le Diff (Avant/Après).
    """
    db = SessionLocal()
    try:
        school_id = st.session_state.get("school_id")
        username = st.session_state.get("username", "system")
        session_id = st.session_state.get("session_id", "SES-PROD-SECURE")
        ip_address = "127.0.0.1"  # Standard local (ou récupération proxy si hébergé sur le web)

        nouveau_log = JournalActivite(
            school_id=school_id,
            timestamp=datetime.now(),
            username=username,
            module=module,
            action=action,
            statut=statut,
            ip_address=ip_address,
            session_id=session_id,
            valeur_avant=str(valeur_avant) if valeur_avant is not None else None,
            valeur_apres=str(valeur_apres) if valeur_apres is not None else None
        )
        db.add(nouveau_log)
        db.commit()
    except Exception as ex:
        db.rollback()
        print(f"Erreur lors de l'enregistrement de l'audit ERP : {ex}")
    finally:
        db.close()

def log_system_exception(source_module, exception_obj):
    """
    Enregistre les plantages et erreurs techniques (System Exception Log) 
    pour isoler les bugs logiciels des erreurs de manipulation humaine.
    """
    db = SessionLocal()
    try:
        tb_str = traceback.format_exc()
        sys_log = SystemLog(
            timestamp=datetime.now(),
            level="ERROR",
            source=source_module,
            message=str(exception_obj),
            stacktrace=tb_str
        )
        db.add(sys_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erreur lors de l'enregistrement du log système : {e}")
    finally:
        db.close()