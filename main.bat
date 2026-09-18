@echo off
setlocal enabledelayedexpansion
cls
echo ================================================
echo BASCULE VERS L'ENVIRONNEMENT DE PRODUCTION
echo ================================================

:: 1. Verification et sauvegarde optionnelle des changements en cours
echo [1/2] Verification de l'etat du depot...
git diff-index --quiet HEAD --
if %errorlevel% neq 0 (
    echo [INFO] Modifications detectees. Sauvegarde en cours...
    git add .
    git commit -m "chore: sauvegarde automatique avant bascule sur main"
) else (
    echo [INFO] Depot propre.
)

:: 2. Passage sur la branche main en toute securite
echo [2/2] Passage sur la branche main (production)...
git checkout main
if %errorlevel% neq 0 goto :error

echo.
echo ================================================
echo VOUS ETES MAINTENANT SUR LA BRANCHE DE PRODUCTION !
echo ================================================
pause
exit /b 0

:error
echo.
echo ================================================
echo [ERREUR] ECHEC DU BASCULEMENT VERS MAIN !
echo Verifiez s'il y a des conflits ou des fichiers bloques.
echo ================================================
pause
exit /b 1