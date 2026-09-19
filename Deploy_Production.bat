@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =================================================================
echo    DEPLOIEMENT OFFICIEL : STAGING VERS PRODUCTION (MAIN)
echo =================================================================

:: 1. Sauvegarde et envoi des modifications en cours sur staging
echo [1/4] Validation et envoi de staging vers GitHub...
git add .
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Mise a jour staging"
)
git push origin staging

:: 2. Bascule forcee sur main et mise a jour
echo.
echo [2/4] Passage sur la branche main (production)...
git checkout -f main
git pull origin main

:: 3. Fusion propre de staging vers main
echo.
echo [3/4] Fusion des modifications de staging vers main...
git merge staging -X theirs
git push origin main
if errorlevel 1 (
    echo [ERREUR] Echec du push GitHub sur main.
    goto ERREUR_FIN
)

:: 4. Retour sécurisé sur staging
echo.
echo [4/4] Retour sur la branche staging...
git checkout staging

echo.
echo =================================================================
echo    DEPLOIEMENT EN PRODUCTION REUSSI AVEC SUCCES !
echo =================================================================
goto FIN

:ERREUR_FIN
echo.
echo =================================================================
echo    [ERREUR CRITIQUE] LE DEPLOIEMENT A ETE ARRETE.
echo =================================================================
git checkout staging

:FIN
pause