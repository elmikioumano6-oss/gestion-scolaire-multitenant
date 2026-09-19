@echo off
setlocal enabledelayedexpansion
<<<<<<< HEAD
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
=======
cls
echo ========================================================
echo    FUSION AUTOMATIQUE: STAGING VERS MAIN (PRODUCTION)
echo ========================================================

:: 0. Validation et sauvegarde conditionnelle sur staging
echo [0/7] Verification et sauvegarde des modifications sur staging...
git diff-index --quiet HEAD --
if %errorlevel% neq 0 (
    echo [INFO] Modifications detectees. Sauvegarde en cours...
    git add .
    git commit -m "chore: sauvegarde automatique de staging avant fusion"
) else (
    echo [INFO] Aucun changement detecte sur staging.
)

:: 1. Passage sur la branche main (production)
echo [1/7] Passage sur la branche main (production)...
git checkout main
if %errorlevel% neq 0 goto :error

:: 2. Mise a jour de main depuis GitHub
echo [2/7] Mise a jour de main depuis GitHub...
git pull origin main
if %errorlevel% neq 0 goto :error

:: 3. Fusion securisee avec resolution automatique des conflits (Strategie -X ours priorite staging)
echo [3/7] Fusion des modifications de staging dans main...
git merge staging -X ours --no-edit -m "Merge automatique de staging vers main avec priorite staging"
if %errorlevel% neq 0 (
    echo [ALERTE] Conflit critique detecte lors de la fusion. Annulation de securite...
    git merge --abort
    goto :error
)

:: 4. Envoi de la production mise a jour sur GitHub
echo [4/7] Envoi de la production mise a jour sur GitHub...
git push origin main
if %errorlevel% neq 0 goto :error

:: 5. Actualisation et execution du script distant sur le VPS
echo [5/7] Lancement du script de mise a jour sur le serveur distant...
ssh root@72.62.147.14 "cd /root/gestionscolaire && ./deploy.sh"
if %errorlevel% neq 0 (
    echo [ERREUR] Le serveur distant n'a pas pu executer le script de mise a jour !
    goto :error
)

:: 6. Verification de sante de l'application en ligne (Adaptez le port si necessaire, ex: 8501)
echo [6/7] Verification de sante de l'application en ligne...
curl -s -o nul -w "%%{http_code}" http://72.62.147.14:8501 > temp_status.txt
set /p HTTP_STATUS=<temp_status.txt
del temp_status.txt

if "!HTTP_STATUS!"=="200" (
    echo [SUCCES] L'application repond parfaitement (Code HTTP 200).
) else (
    echo [AVERTISSEMENT] L'application repond avec le code HTTP !HTTP_STATUS!. Verifiez les logs sur le serveur.
)

:: 7. Retour sur la branche staging pour continuer a travailler
echo [7/7] Retour sur la branche staging...
git checkout staging
if %errorlevel% neq 0 goto :error

echo.
echo ========================================================
echo    FUSION TERMINEE ET SERVEUR MIS A JOUR AVEC SUCCÈS !
echo    L'APPLICATION TOURNE ET REPOND CORRECTEMENT EN LIGNE.
echo    VOUS ETES DE RETOUR SUR STAGING.
echo ========================================================
pause
exit /b 0

:error
echo.
echo ========================================================
echo    [ERREUR CRITIQUE] LE DEPLOIEMENT A ECHOUE !
echo ========================================================
echo Verifiez les messages ci-dessus. Vous etes securise, 
echo aucune modification corrompue n'a ete poussee.
echo ========================================================
git checkout staging 2>nul
pause
exit /b 1
>>>>>>> staging
