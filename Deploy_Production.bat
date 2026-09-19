@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =================================================================
echo    DEPLOIEMENT OFFICIEL : STAGING VERS PRODUCTION (MAIN)
echo =================================================================

:: 1. Validation et synchronisation de l'environnement de staging
echo [1/4] Synchronisation de staging vers GitHub...
git checkout staging >nul 2>&1
git add .
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "chore: auto-commit staging avant release"
)
git push origin staging
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Echec du push sur staging.
    goto ERREUR_FIN
)

:: 2. Bascule contrôlée vers la branche de production (main)
echo.
echo [2/4] Bascule vers la branche main (production)...
git checkout main
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Impossible de basculer sur main.
    goto ERREUR_FIN
)
git pull origin main

:: 3. Fusion des nouveautés validées de staging vers main
echo.
echo [3/4] Fusion de staging vers main...
git merge staging -m "Release: merge staging into main (Production)" -X theirs
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Conflit de fusion detecte.
    goto ERREUR_FIN
)

:: 4. Publication sur le dépôt distant et retour au mode dev (staging)
echo.
echo [4/4] Publication sur GitHub et retour sur staging...
git push origin main
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Echec du push sur main.
    goto ERREUR_FIN
)

git checkout staging
echo.
echo =================================================================
echo    DEPLOIEMENT EN PRODUCTION REUSSI ET SECURISE !
echo =================================================================
goto FIN

:ERREUR_FIN
echo.
echo =================================================================
echo    [ERREUR] INTERRUPTION DU DEPLOIEMENT PAR SECURITE.
echo =================================================================
git checkout staging
pause
color 0C
exit /b 1

:FIN
pause
color 07