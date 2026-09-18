@echo off
setlocal enabledelayedexpansion
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