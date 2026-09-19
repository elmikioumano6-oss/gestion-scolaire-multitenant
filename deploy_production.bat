@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo    DEPLOIEMENT OFFICIEL : STAGING VERS PRODUCTION (MAIN)
echo ========================================================

:: 0. Sauvegarde propre et securisation de l'etat local staging
echo [1/5] Sauvegarde et validation des modifications sur staging...
git checkout staging >nul 2>&1
git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "chore: mise a jour automatique staging avant release"
)
git push origin staging
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Echec de la synchronisation de staging.
    goto :error
)

:: 1. Passage sur la branche main (production)
echo [2/5] Passage sur la branche main (production)...
git checkout -f main
if errorlevel 1 goto :error

:: 2. Mise a jour de main depuis GitHub
echo [3/5] Synchronisation de main depuis GitHub...
git pull origin main
if errorlevel 1 goto :error

:: 3. Fusion securisee de staging vers main
echo [4/5] Fusion des nouveautes de staging vers main...
git merge staging --no-edit -m "Release: merge staging into main (Production)"
if errorlevel 1 (
    echo [ALERTE] Conflit detecte lors de la fusion. Annulation de securite...
    git merge --abort
    goto :error
)

:: 4. Envoi de la production sur GitHub (Le VPS recupèrera cela à 20h)
echo [5/5] Publication de la production sur GitHub...
git push origin main
if errorlevel 1 goto :error

:: 5. Retour securise et propre sur staging pour reprendre le travail
echo.
echo [INFO] Retour sur l'environnement de staging...
git checkout -f staging
git pull origin staging >nul 2>&1

echo.
echo ========================================================
echo    DEPLOIEMENT EN PRODUCTION REUSSI AVEC SUCCÈS !
echo    Le code est sur GitHub, le VPS se chargera de la 
::    synchronisation automatique a 20h00.
echo    Vous etes de retour sur staging en toute securite.
echo ========================================================
pause
exit /b 0

:error
echo.
echo ========================================================
echo    [ERREUR CRITIQUE] LE DEPLOIEMENT A ETE INTERROMPU !
echo ========================================================
echo Securite activee : annulation et retour force sur staging.
echo ========================================================
git checkout -f staging 2>nul
pause
exit /b 1