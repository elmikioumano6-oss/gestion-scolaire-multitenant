@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo    DEPLOIEMENT OFFICIEL : STAGING VERS PRODUCTION (MAIN)
echo ========================================================

echo [1/4] Sauvegarde de staging...
git checkout staging
git add -A
git diff --cached --quiet
if errorlevel 1 git commit -m "chore: sync staging"
git push origin staging
if errorlevel 1 goto :ERREUR

echo [2/4] Passage sur main...
git checkout main
git pull origin main
if errorlevel 1 goto :ERREUR

echo [3/4] Fusion vers main...
git merge staging --no-edit -m "Release: merge staging into main"
if errorlevel 1 (
    git merge --abort
    goto :ERREUR
)
git push origin main
if errorlevel 1 goto :ERREUR

echo [4/4] Retour sur staging...
git checkout staging
git merge main --no-edit
git push origin staging

echo ========================================================
echo    SUCCES TOTAL !
echo ========================================================
pause
exit /b 0

:ERREUR
echo ========================================================
echo    [ERREUR] LE DEPLOIEMENT A ECHOUE.
echo ========================================================
git checkout staging 2>nul
pause
exit /b 1