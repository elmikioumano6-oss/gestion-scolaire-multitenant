@echo off
setlocal enabledelayedexpansion
<<<<<<< HEAD
cd /d "%~dp0"

echo =================================================================
echo    DEPLOIEMENT EXPERT - GESTION SCOLAIRE PRO (STAGING)
echo =================================================================
echo.

:: --- 1. VERIFICATION DE L'ENVIRONNEMENT LOCAL ---
echo [etape 1/5] Verification de l'environnement Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Git n'est pas installe ou introuvable.
    goto ERREUR_FIN
)
if not exist ".git" (
    echo [ERREUR] Ce dossier n'est pas un depot Git valide.
    goto ERREUR_FIN
)

:: --- 1.5. BASCULE SUR LA BRANCHE STAGING ---
git checkout staging >nul 2>&1
if errorlevel 1 (
    echo [INFO] Creation et bascule sur la branche staging...
    git checkout -b staging
)

:: --- 2. INDEXATION ET COMMIT AUTOMATIQUE ---
echo.
echo [etape 2/5] Preparation et indexation des fichiers (staging)...
git add .
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Mise a jour automatique de l'ERP - Staging"
) else (
    echo [INFO] Aucun nouveau fichier modifie a commiter. Poursuite...
)

:: --- 3. ENVOI VERS GITHUB ---
echo.
echo [etape 3/5] Envoi du code source vers le depot GitHub (staging)...
git push origin staging
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Echec du push GitHub sur staging. Verifiez votre connexion.
    goto ERREUR_FIN
)

:: --- 4. VERIFICATION DU TUNNEL SSH LOCAL ---
echo.
echo [etape 4/5] Verification du tunnel SSH pour la base de donnees...
netstat -ano | findstr "5432" >nul
if errorlevel 1 (
    echo [ATTENTION] Le port 5432 n'est pas ouvert localement. Le tunnel SSH vers le VPS est-il lance ?
    choice /C ON /M "Voulez-vous continuer malgre tout"
    if errorlevel 2 goto ERREUR_FIN
)

:: --- 5. TESTS DE SANTE ET INTEGRITE POST-DEPLOIEMENT ---
echo.
echo [etape 5/5] Execution des diagnostics de la base de donnees...
if exist test_conn.py (
    python test_conn.py
    if !errorlevel! neq 0 (
        echo [ERREUR CRITIQUE] Le test de connexion a la base de donnees a echoue.
        goto ERREUR_FIN
    )
)

if exist tester_all_tables.py (
    python tester_all_tables.py
    if !errorlevel! neq 0 (
        echo [ERREUR CRITIQUE] L'integrite des tables de l'ERP est compromise.
        goto ERREUR_FIN
    )
)

echo.
echo =================================================================
echo    DEPLOIEMENT STAGING REUSSI : CODE POUSSE ET VERIFIE !
echo =================================================================
goto FIN

:ERREUR_FIN
echo.
echo =================================================================
echo    [ERREUR CRITIQUE] LE DEPLOIEMENT A ETE ARRETE PAR SECURITE.
echo =================================================================
color 0C

:FIN
pause
color 07
=======
cls
echo ================================================
echo    BASCULEMENT DE MAIN VERS STAGING
echo ================================================

:: 1. Sauvegarde propre des changements en cours sur main si existants
echo [1/3] Verification et sauvegarde sur main...
git diff-index --quiet HEAD --
if %errorlevel% neq 0 (
    echo [INFO] Changements detectes. Sauvegarde en cours...
    git add .
    git commit -m "chore: sauvegarde automatique avant bascule sur staging"
) else (
    echo [INFO] Aucun changement a commiter sur main.
)

:: 2. Passage sur la branche staging
echo [2/3] Passage sur la branche staging...
git checkout staging
if %errorlevel% neq 0 goto :error

:: 3. Mise a jour de staging depuis GitHub
echo [3/3] Mise a jour de staging depuis GitHub...
git pull origin staging
if %errorlevel% neq 0 goto :error

echo.
echo ================================================
echo    VOUS ETES MAINTENANT SUR LA BRANCHE STAGING !
echo ================================================
pause
exit /b 0

:error
echo.
echo ================================================
echo    [ERREUR] LE BASCULEMENT A ECHOUE !
echo ================================================
pause
exit /b 1
>>>>>>> staging
