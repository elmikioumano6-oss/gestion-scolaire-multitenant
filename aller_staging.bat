@echo off
cls
echo ================================================
echo BASCULEMENT DE MAIN VERS STAGING
echo ================================================

echo 1. Sauvegarde des changements en cours sur main...
git add .
git commit -m "chore: sauvegarde automatique avant bascule" || echo Rien a commiter

echo 2. Passage sur la branche staging...
git checkout staging

echo 3. Mise a jour de staging depuis GitHub...
git pull origin staging

echo.
echo ================================================
echo VOUS ETES MAINTENANT SUR LA BRANCHE STAGING !
echo ================================================
pause