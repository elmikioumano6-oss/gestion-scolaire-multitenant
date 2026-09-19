@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo    DEPLOIEMENT PROFESSIONNEL : STAGING VERS MAIN
echo ========================================================

:: 1. Validation de l'etat local de staging
echo [1/4] Validation de la branche staging...
git checkout staging
if errorlevel 1 goto :ERREUR

git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "chore: synchronisation automatique staging"
)
git push origin staging
if errorlevel 1 goto :ERREUR

:: 2. Bascule et mise a jour de main
echo [2/4] Preparation de la production (main)...
git checkout main
if errorlevel 1 goto :ERREUR

git pull origin main
if errorlevel 1 goto :ERREUR

:: 3. Fusion propre de staging vers main
echo [3/4] Fusion des evolutions vers main...
git merge staging --no-edit -m "Release: merge staging into main"
if errorlevel 1 (
    echo [ERREUR] Conflit detecte lors de la fusion. Annulation...
    git merge --abort
    goto :ERREUR
)

git push origin main
if errorlevel 1 goto :ERREUR

:: 4. Realignement propre de staging
echo [4/4] Alignement final de staging...
git checkout staging
git merge main --no-edit
git push origin staging

echo.
echo ========================================================
echo    DEPLOIEMENT ET SYNCHRONISATION TERMINES AVEC SUCCES !
echo ========================================================
pause
exit /b 0

:ERREUR
echo.
echo ========================================================
echo    [ERREUR] LE DEPLOIEMENT A ECHOUE.
echo ========================================================
git checkout staging 2>nul
pause
exit /b 1