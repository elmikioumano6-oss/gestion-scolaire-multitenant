import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
url = os.getenv(
    "DATABASE_URL",
    "postgresql://erp_user:Rahmatfh2026@127.0.0.1:5432/school_erp",
)
print("URL:", url)

try:
    conn = psycopg2.connect(url)
    print("Connexion reussie !")
    conn.close()
except Exception as e:
    print("Erreur:", e)