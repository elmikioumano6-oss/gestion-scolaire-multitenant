import os
import sys
from dotenv import load_dotenv
import psycopg2

load_dotenv(override=True)

# On force l'URL exacte pour éviter qu'une ancienne variable système ne prenne le dessus
url = os.getenv("DATABASE_URL")
if not url or "supabase" in url:
    url = "postgresql://erp_user:Rahmatfh2026@127.0.0.1:5432/school_erp"

print("URL ciblee:", url)

try:
    conn = psycopg2.connect(url)
    print("Connexion reussie !")
    conn.close()
    sys.exit(0)
except Exception as e:
    print("Erreur:", e)
    sys.exit(1)