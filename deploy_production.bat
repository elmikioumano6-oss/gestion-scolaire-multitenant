@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo    MODE DIAGNOSTIC : DEPLOIEMENT STAGING VERS MAIN
echo ========================================================

:: 1. Sauvegarde et validation sur staging
echo [1/5] Sauvegarde et validation des modifications sur staging...
git checkout staging
if errorlevel 1 goto :DEBUG_ERREUR

git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "chore: mise a jour automatique staging avant release"
)

git push origin staging
if errorlevel 1 goto :DEBUG_ERREUR

:: 2. Passage sur main
echo [2/5] Passage sur main...
git checkout -f main
if errorlevel 1 goto :DEBUG_ERREUR

:: 3. Pull main
echo [3/5] Synchronisation de main...
git pull origin main
if errorlevel 1 goto :DEBUG_ERREUR

:: 4. Merge staging
echo [4/5] Fusion des modifications...
git merge staging --no-edit -m "Release: merge staging into main"
if errorlevel 1 goto :DEBUG_ERREUR

git push origin main
if errorlevel 1 goto :DEBUG_ERREUR

:: 5. Retour sur staging
echo [5/5] Retour sur staging...
git checkout -f staging
git pull origin main
git push origin staging

echo.
echo ========================================================
echo    SUCCES TOTAL !
echo ========================================================
pause
exit /b 0

:DEBUG_ERREUR
echo.
echo ========================================================
echo    [ERREUR BLOQUEE] LE SCRIPT S'EST ARRETE ICI.
echo ========================================================
pause
exit /b 1