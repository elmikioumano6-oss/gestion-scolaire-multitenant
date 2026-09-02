@echo off
color 0A
echo ========================================
echo   SYNCHRONISATION RAHMAT-FH
echo ========================================

echo [1/3] Verification et recuperation des mises a jour...
git pull

echo [2/3] Preparation et sauvegarde des modifications...
git add .
git commit -m "Mise a jour automatique CSP RAHMAT-FH"

echo [3/3] Envoi sur GitHub (Mise a jour du Cloud)...
git push

echo ========================================
echo   OPERATION TERMINEE AVEC SUCCES !
echo ========================================
pause