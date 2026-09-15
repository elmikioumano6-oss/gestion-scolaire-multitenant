@echo off
echo [1/2] Lancement du tunnel SSH persistant vers le serveur distant...
:: Ajout de -C pour compresser le trafic et accélérer les requêtes locales
start cmd /k "ssh -C -N -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -L 5432:localhost:5432 root@72.62.147.14"

echo [2/2] Attente de 3 secondes pour l'etablissement du tunnel...
timeout /t 3 /nobreak > nul

echo [3/3] Lancement de l'application Streamlit en local...
cd /d "C:\Users\Pc\Desktop\gestion_scolaire_pro"
streamlit run app.py