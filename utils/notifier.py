import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from database.db_config import SessionLocal
from database.models import SystemLog

# =================CONFIGURATION DES ALERTES=================
# Telegram
TELEGRAM_BOT_TOKEN = "8994891137:AAEDUAOF1cmrE-E5SPmOV2ia6ARJAroRq18"
TELEGRAM_CHAT_ID = "8972776383"

# Email (SMTP Gmail)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "elmikioumano6@gmail.com"
SMTP_PASSWORD = "aeny spic jhab tnob"
EMAIL_DESTINATAIRE = "elmikioumano6@gmail.com"
# ===========================================================


def send_alert(message, level="ERROR"):
    """
    Enregistre l'alerte en base de données (table system_logs) et l'envoie 
    simultanément par Telegram et par Email.
    """
    # 1. Enregistrement dans la base de données
    db = SessionLocal()
    try:
        log_entry = SystemLog(
            level=level,
            source="Monitoring Gardien",
            message=message,
            stacktrace=traceback.format_exc() if level == "ERROR" else None
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    formatted_message = f"🚨 *[ALERTE GESTION SCOLAIRE PRO]* 🚨\n\n*Niveau:* {level}\n*Message:* {message}"

    # 2. Envoi de la notification push (Telegram)
    if TELEGRAM_BOT_TOKEN != "VOTRE_TOKEN_BOT_TELEGRAM":
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": formatted_message,
                "parse_mode": "Markdown"
            }
            requests.post(url, json=payload, timeout=3)
        except Exception:
            pass  # Évite de bloquer l'application si le réseau est coupé

    # 3. Envoi de l'alerte par Email
    if SMTP_USER != "votre_email@gmail.com":
        try:
            msg = MIMEMultipart()
            msg["From"] = SMTP_USER
            msg["To"] = EMAIL_DESTINATAIRE
            msg["Subject"] = f"[{level}] Alerte Critique - Gestion Scolaire Pro"

            body = f"Bonjour,\n\nUne alerte système a été déclenchée sur la plateforme :\n\nNiveau : {level}\nMessage :\n{message}\n\n---\nSystème de monitoring automatique - Gestion Scolaire Pro"
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, EMAIL_DESTINATAIRE, msg.as_string())
            server.quit()
        except Exception:
            pass  # Évite de bloquer l'application si le serveur mail échoue