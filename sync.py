@echo off
cls
echo ==========================================
echo   SAUVEGARDE & SYNCHRONISATION CSP-RAHMAT-FH
echo ==========================================
echo.

echo [1/3] Execution de la sauvegarde locale de la base de donnees...
python sauvegarde.py
echo.

echo [2/3] Ajout et validation des modifications du code...
git add .
set /p message="Entrez votre message de mise a jour (ou appuyez sur Entree) : "
if "%message%"=="" set message="Mise automatique CSP-Rahmat-FH"
git commit -m "%message%"
echo.

echo [3/3] Envoi vers le serveur distant (GitHub via 3G)...
git push origin main

echo.
echo ==========================================
echo   TOUT EST ENREGISTRE ET SYNCHRONISE !
echo ==========================================
pause