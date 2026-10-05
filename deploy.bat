@echo off
SETLOCAL EnableEXTENSIONS
SETLOCAL EnableDelayedExpansion

TITLE Deploiement et Workflow - Gestion Scolaire Pro
COLOR 0B

ECHO ========================================================
ECHO    GESTION SCOLAIRE PRO - WORKFLOW ET DEPLOIEMENT RAPIDE
ECHO ========================================================
ECHO.

:: 1. Vérification stricte de la branche locale
FOR /F "tokens=*" %%i IN ('git branch --show-current') DO SET CURRENT_BRANCH=%%i

IF NOT "%CURRENT_BRANCH%"=="staging" (
    COLOR 0C
    ECHO.
    ECHO [ERREUR] Vous devez imperativement etre sur la branche 'staging'.
    GOTO :error_exit
)

:: 2. Affichage des modifications et publication vers le distant (main)
ECHO [1/3] Fichiers et vues modifies :
git status -s
ECHO.

git add .
git commit -m "Mise à jour automatique staging -> main - %DATE% %TIME%"
git push origin staging:main --force-with-lease
IF ERRORLEVEL 1 (
    COLOR 0C
    ECHO [ERREUR CRITIQUE] Le push vers 'main' a echoue.
    GOTO :error_exit
)
ECHO [OK] Publie avec succes sur 'main'.

:: 3. Exécution optionnelle des migrations de base de données
ECHO.
ECHO [2/3] Verification des migrations de base de donnees...
IF EXIST migrate.py (
    call python migrate.py
) ELSE IF EXIST init_db.py (
    call python init_db.py
) ELSE (
    ECHO [INFO] Aucun script de migration requis.
)

:: Succès Global
COLOR 0A
ECHO.
ECHO ========================================================
ECHO    TERMINE AVEC SUCCES ! (Vous etes sur staging)
ECHO ========================================================
GOTO :end

:error_exit
COLOR 0C
ECHO.
ECHO ========================================================
ECHO    OPERATION INTERROMPUE
ECHO ========================================================

:end
ECHO.
PAUSE >NUL
ENDLOCAL
EXIT /B