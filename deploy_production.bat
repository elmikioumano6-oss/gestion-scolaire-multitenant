@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo    DEPLOIEMENT : STAGING VERS PRODUCTION
echo ========================================================

REM Verification du depot Git
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Le script ne se trouve pas dans un depot Git.
    goto :ERREUR
)

echo.
echo [1/4] Sauvegarde et envoi de staging...

git checkout staging
if errorlevel 1 goto :ERREUR

git add -A
if errorlevel 1 goto :ERREUR

git diff --cached --quiet
if errorlevel 1 (
    echo Creation d'un commit de synchronisation...
    git commit -m "chore: sync staging"
    if errorlevel 1 goto :ERREUR
) else (
    echo Aucune nouvelle modification a enregistrer.
)

git push origin staging
if errorlevel 1 goto :ERREUR

echo.
echo [2/4] Mise a jour de main...

git checkout main
if errorlevel 1 goto :ERREUR

git pull --ff-only origin main
if errorlevel 1 goto :ERREUR

echo.
echo [3/4] Fusion de staging vers main...

git merge staging --no-ff -m "Release: merge staging into main"
if errorlevel 1 (
    echo [ERREUR] Conflit pendant la fusion vers main.
    git merge --abort >nul 2>&1
    goto :ERREUR
)

git push origin main
if errorlevel 1 goto :ERREUR

echo.
echo [4/4] Retour sur staging...

git checkout staging
if errorlevel 1 goto :ERREUR

echo.
echo ========================================================
echo    DEPLOIEMENT REUSSI
echo    Le VPS peut maintenant recuperer la branche main.
echo    Vous etes revenu sur staging.
echo ========================================================
pause
exit /b 0

:ERREUR
echo.
echo ========================================================
echo    [ERREUR] LE DEPLOIEMENT A ECHOUE
echo ========================================================
echo Consultez les messages Git affiches ci-dessus.

git merge --abort >nul 2>&1
git checkout staging >nul 2>&1

echo Appuyez sur une touche pour quitter...
pause >nul
exit /b 1