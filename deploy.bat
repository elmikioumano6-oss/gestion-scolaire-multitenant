@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =================================================================
echo    DEPLOIEMENT EXPERT - GESTION SCOLAIRE PRO (PRODUCTION)
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

:: --- 2. INDEXATION ET COMMIT AUTOMATIQUE ---
echo.
echo [etape 2/5] Preparation et indexation des fichiers...
git add .
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Mise a jour automatique de l'ERP - Production"
) else (
    echo [INFO] Aucun nouveau fichier modifie a commiter. Poursuite...
)

:: --- 3. ENVOI VERS GITHUB ---
echo.
echo [etape 3/5] Envoi du code source vers le depot GitHub (main)...
git push origin main
if errorlevel 1 (
    echo [ERREUR CRITIQUE] Echec du push GitHub. Verifiez votre connexion.
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

:: --- 5. TESTS DE SANTE ET INTEGRITE POST-DEPLOIEMENT (CORRIGE) ---
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
echo    DEPLOIEMENT REUSSI : CODE POUSSE ET SYSTEME VERIFIE !
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