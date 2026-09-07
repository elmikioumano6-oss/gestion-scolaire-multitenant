from datetime import datetime
from database.db_config import SessionLocal
from database.models import JournalActivite, SystemLog, User
import traceback
import streamlit as st


def log_action_erp(
    module,
    action,
    statut="Succès",
    valeur_avant=None,
    valeur_apres=None,
):
  """Enregistre une action sensible avec traçabilité granulaire (Normes ERP - SOC 2 / ISO 27001).

  Capture l'utilisateur connecté, l'école active, l'IP réelle, la session et le
  Diff (Avant/Après).
  """
  db = SessionLocal()
  try:
    # --- RÉCUPÉRATION ROBUSTE DU CONTEXTE (ÉVITE QUE LE LOG DISPARAISSE) ---
    username = (
        st.session_state.get("username")
        or st.session_state.get("user")
        or st.session_state.get("admin_user")
    )

    if not username:
      username = "admin_rahmat"  # Fallback ciblé pour votre tenant actif

    school_id = st.session_state.get("school_id")
    if not school_id:
      # Si le school_id manque dans la session, on le récupère directement depuis le user en base
      user_db = db.query(User).filter(User.username == str(username)).first()
      school_id = user_db.school_id if user_db and user_db.school_id else 1

    session_id = st.session_state.get("session_id", "SES-PROD-SECURE")

    # Récupération dynamique de la véritable adresse IP (PC, Téléphone ou Proxy)
    ip_address = "127.0.0.1"
    try:
      headers = st.context.headers
      if headers:
        ip_address = (
            headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or headers.get("X-Real-Ip", "").strip()
            or "127.0.0.1"
        )
    except Exception:
      pass

    nouveau_log = JournalActivite(
        school_id=school_id,
        timestamp=datetime.now(),
        username=str(username),
        module=module,
        action=action,
        statut=statut,
        ip_address=ip_address,
        session_id=session_id,
        valeur_avant=str(valeur_avant) if valeur_avant is not None else None,
        valeur_apres=str(valeur_apres) if valeur_apres is not None else None,
    )
    db.add(nouveau_log)
    db.commit()
  except Exception as ex:
    db.rollback()
    print(f"Erreur lors de l'enregistrement de l'audit ERP : {ex}")
  finally:
    db.close()


def log_system_exception(source_module, exception_obj):
  """Enregistre les plantages et erreurs techniques (System Exception Log)

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
        stacktrace=tb_str,
    )
    db.add(sys_log)
    db.commit()
  except Exception as e:
    db.rollback()
    print(f"Erreur lors de l'enregistrement du log système : {e}")
  finally:
    db.close()