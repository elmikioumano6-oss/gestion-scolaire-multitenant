@echo off
title Lancement ERP Scolaire - Local (Staging)
cls
echo ========================================================
echo        LANCEMENT DE L'ENVIRONNEMENT LOCAL (STAGING)
echo ========================================================

:: 1. Se placer directement dans le dossier du projet
cd /d "C:\Users\Pc\Desktop\gestion_scolaire_pro"
if %errorlevel% neq 0 (
    echo [ERREUR] Le dossier du projet est introuvable !
    pause
    exit /b 1
)

:: 2. S'assurer qu'on est bien sur staging pour coder
echo [INFO] Verification de la branche Git active...
git checkout staging >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Creation et bascule sur la branche staging...
    git checkout -b staging
)

:: 3. Lancement du tunnel SSH persistant et optimisé vers le serveur distant
echo.
echo [1/2] Lancement du tunnel SSH persistant vers le serveur distant...
:: -C active la compression du trafic pour accélérer les requêtes de la base de données
:: -o ServerAliveInterval=15 envoie un signal toutes les 15s pour empêcher la coupure par inactivité
:: -o ServerAliveCountMax=5 nombre d'essais avant de considérer la connexion perdue
:: -o TCPKeepAlive=yes maintient la couche TCP active
start cmd /k "title Tunnel SSH PostgreSQL & ssh -C -N -o ServerAliveInterval=15 -o ServerAliveCountMax=5 -o TCPKeepAlive=yes -L 5432:localhost:5432 root@72.62.147.14"

echo [2/2] Attente de 3 secondes pour l'etablissement du tunnel...
timeout /t 3 /nobreak > nul

:: 4. Lancement de l'application Streamlit en local
echo.
echo [3/3] Lancement de l'application Streamlit en local (Staging)...
streamlit run app.py
pause