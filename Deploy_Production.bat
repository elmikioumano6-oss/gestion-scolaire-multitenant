@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =================================================================
echo    DEPLOIEMENT OFFICIEL : STAGING VERS PRODUCTION (MAIN)
echo =================================================================

:: 1. SECURISATION TOTALE DE STAGING (Y COMPRIS LE SCRIPT LOCAL)
echo [1/4] Enregistrement et envoi de tout l'etat local sur staging...
git checkout staging >nul 2>&1
git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "chore: sync complete avant release production"
)
git push origin staging
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Echec du push sur staging.
    goto ERREUR_FIN
)

:: 2. BASCULE PROPRE VERS MAIN ET MISE A JOUR
echo.
echo [2/4] Bascule vers la branche main (production)...
git checkout -f main
git pull origin main

:: 3. FUSION DES NOUVEAUTES DE STAGING VERS MAIN
echo.
echo [3/4] Fusion des modifications de staging vers main...
git merge staging -m "Release: merge staging into main (Production)" -X theirs
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Conflit de fusion detecte.
    goto ERREUR_FIN
)

:: 4. PUBLICATION SUR GITHUB ET RETOUR COMPLET SUR STAGING
echo.
echo [4/4] Publication sur GitHub et retour securise sur staging...
git push origin main
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Echec du push sur main.
    goto ERREUR_FIN
)

:: ON RAMENE TOUT PROPREMENT SUR STAGING SANS AUCUN OUBLI
git checkout -f staging
git pull origin staging
echo.
echo =================================================================
echo    DEPLOIEMENT EN PRODUCTION REUSSI ET ENTIEREMENT SECURISE !
echo =================================================================
goto FIN

:ERREUR_FIN
echo.
echo =================================================================
echo    [ERREUR] LE DEPLOIEMENT A ETE INTERROMPU PAR SECURITE.
echo =================================================================
git checkout -f staging
pause
color 0C
exit /b 1

:FIN
pause
color 07