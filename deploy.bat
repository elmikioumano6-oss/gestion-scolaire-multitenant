@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo   DEPLOIEMENT EXPERT - GESTION SCOLAIRE
echo ========================================================
echo.

:: 1. CONTROLE GIT
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Git n'est pas installe.
    goto ERREUR_FIN
)
if not exist ".git" (
    echo [ERREUR] Ce dossier n'est pas un depot Git.
    goto ERREUR_FIN
)

:: 2. ENREGISTREMENT ET COMMIT
echo [1/3] Indexation et envoi des fichiers...
git add .
git commit -m "Mise a jour automatique - Production"

:: 3. POUSSEE VERS GITHUB
echo.
echo [2/3] Envoi vers GitHub...
git push origin main
if errorlevel 1 (
    echo [ERREUR] Echec du push GitHub.
    goto ERREUR_FIN
)

:: 4. VERIFICATION DE LA BASE DE DONNEES
echo.
echo [3/3] Verification de la connexion PostgreSQL...
if exist test_conn.py (
    python test_conn.py
)

echo.
echo ========================================================
echo   DEPLOIEMENT TERMINE AVEC SUCCES !
echo ========================================================
goto FIN

:ERREUR_FIN
echo.
echo ========================================================
echo   [ERREUR] LE DEPLOIEMENT A ETE INTERROMPU.
echo ========================================================

:FIN
pause