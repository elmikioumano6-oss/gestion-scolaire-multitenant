@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =================================================================
echo    DEPLOIEMENT OFFICIEL : STAGING VERS PRODUCTION (MAIN)
echo =================================================================

:: 1. Validation de l'etape staging
echo [1/4] Envoi des modifications staging vers GitHub...
git checkout staging >nul 2>&1
git add .
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Mise a jour staging"
)
git push origin staging

:: 2. Bascule forcee sur main
echo.
echo [2/4] Passage sur la branche main (production)...
git checkout -f main
git pull origin main

:: 3. Fusion et publication forcee
echo.
echo [3/4] Fusion des modifications vers main...
git merge staging -m "Merge staging into main" -X theirs
git push origin main
if errorlevel 1 (
    echo [ERREUR] Echec de la publication sur GitHub.
    goto ERREUR_FIN
)

:: 4. Retour force sur staging
echo.
echo [4/4] Retour sur l'environnement de staging...
git checkout -f staging

echo.
echo =================================================================
echo    DEPLOIEMENT EN PRODUCTION REUSSI AVEC SUCCES !
echo =================================================================
goto FIN

:ERREUR_FIN
echo.
echo =================================================================
echo    [ERREUR] LE DEPLOIEMENT A ETE INTERROMPU.
echo =================================================================
git checkout -f staging
pause
exit /b 1

:FIN
pause