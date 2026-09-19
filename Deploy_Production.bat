@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =================================================================
echo    DEPLOIEMENT OFFICIEL EN PRODUCTION (BRANCHE MAIN)
echo =================================================================
echo.

:: --- 1. VERIFICATION DE L'ENVIRONNEMENT ---
echo [etape 1/4] Verification de l'environnement Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Git n'est pas installe ou introuvable.
    goto ERREUR_FIN
)

:: --- 2. BASCULE ET FUSION DEPUIS STAGING ---
echo.
echo [etape 2/4] Bascule sur main et recuperation de staging...
git checkout main
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Impossible de basculer sur main.
    goto ERREUR_FIN
)

git pull origin main
git merge staging -m "Merge branch 'staging' into main (Mise en production)"
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Conflit détecté lors de la fusion avec staging. Veuillez le résoudre manuellement.
    goto ERREUR_FIN
)

:: --- 3. ENVOI VERS GITHUB (PRODUCTION) ---
echo.
echo [etape 3/4] Envoi de la production vers GitHub (main)...
git push origin main
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Echec du push GitHub sur main.
    goto ERREUR_FIN
)

:: --- 4. RETOUR SUR STAGING POUR CONTINUER LE TRAVAIL ---
echo.
echo [etape 4/4] Retour sur la branche staging pour la suite du dev...
git checkout staging

echo.
echo =================================================================
echo    DEPLOIEMENT EN PRODUCTION REUSSI AVEC SUCCES !
echo =================================================================
goto FIN

:ERREUR_FIN
echo.
echo =================================================================
echo    [ERREUR] LE DEPLOIEMENT EN PRODUCTION A ECHOUE.
echo =================================================================
color 0C

:FIN
pause
color 07