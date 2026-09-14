@echo off
echo [1/2] Lancement du tunnel SSH persistant vers le serveur distant...
:: -o ServerAliveInterval=60 envoie un signal toutes les 60s pour empêcher la coupure par inactivité
:: -o ServerAliveCountMax=3 relance si le serveur ne répond plus
start cmd /k "ssh -N -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -L 5432:localhost:5432 root@72.62.147.14"

echo [2/2] Attente de 3 secondes pour l'etablissement du tunnel...
timeout /t 3 /nobreak > nul

echo [3/3] Lancement de l'application Streamlit en local...
cd /d "C:\Users\Pc\Desktop\gestion_scolaire_pro"
streamlit run app.py