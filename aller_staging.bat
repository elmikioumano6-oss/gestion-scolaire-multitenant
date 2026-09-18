@echo off
setlocal enabledelayedexpansion
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