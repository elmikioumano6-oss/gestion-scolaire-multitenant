import os
import sys
from dotenv import load_dotenv
import psycopg2

load_dotenv()

# Récupération de l'URL de connexion (priorité au .env, sinon fallback sur le tunnel local/VPS)
url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Rahmatfh2026@127.0.0.1:5432/postgres",
)
print("URL:", url)

try:
    conn = psycopg2.connect(url)
    print("Connexion reussie !")
    conn.close()
    sys.exit(0)
except Exception as e:
    print("Erreur:", e)
    sys.exit(1)