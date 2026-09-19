@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =================================================================
echo    DEPLOIEMENT OFFICIEL : STAGING VERS PRODUCTION (MAIN)
echo =================================================================

:: 1. Enregistrement des derniers changements sur staging s'il y en a
echo [1/5] Sauvegarde des modifications en cours sur staging...
git add .
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Mise a jour automatique avant bascule en production"
)
git push origin staging

:: 2. Bascule sur main et recuperation
echo.
echo [2/5] Passage sur la branche main (production)...
git checkout main
git pull origin main

:: 3. Fusion de staging vers main en forçant les nouveautés
echo.
echo [3/5] Fusion des nouveautes de staging vers main...
git merge staging -m "Merge branch 'staging' into main (Mise en production)" -X theirs
if errorlevel 1 (
    echo [ERREUR] Un conflit bloque la fusion.
    goto ERREUR_FIN
)

:: 4. Envoi sur GitHub (main)
echo.
echo [4/5] Envoi du code de production vers GitHub (main)...
git push origin main
if errorlevel 1 (
    echo [ERREUR] Echec du push GitHub sur main.
    goto ERREUR_FIN
)

:: 5. Retour sécurisé sur staging
echo.
echo [5/5] Retour sur la branche staging pour la suite du developpement...
git checkout staging

echo.
echo =================================================================
echo    DEPLOIEMENT EN PRODUCTION REUSSI ET SECURISE !
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