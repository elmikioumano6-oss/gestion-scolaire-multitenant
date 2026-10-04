@echo off
SETLOCAL EnableEXTENSIONS
SETLOCAL EnableDelayedExpansion

TITLE Deploiement - Gestion Scolaire Pro [Staging]
COLOR 0B

ECHO ========================================================
ECHO    DEPLOIEMENT AUTOMATISE - GESTION SCOLAIRE PRO
ECHO ========================================================
ECHO.

:: 0. Sécurisation et envoi des modifications locales vers main si nécessaire
ECHO [0/3] Envoi des modifications vers GitHub (branche main)...
call git add .
call git commit -m "Mise à jour automatique staging - %DATE% %TIME%"
call git push origin main
IF ERRORLEVEL 1 (
    ECHO [INFO] Aucun changement à commuter ou push optionnel déjà à jour sur main.
)

:: 1. Synchronisation Git (Fusion de main vers staging ou pull staging)
ECHO.
ECHO [1/3] Synchronisation du code source (GitHub - staging)...
call git checkout staging
call git pull origin staging
IF ERRORLEVEL 1 (
    COLOR 0C
    ECHO.
    ECHO [ERREUR CRITIQUE] La synchronisation Git a echoue.
    GOTO :error_exit
)

:: 2. Dépendances Python
ECHO.
ECHO [2/3] Verification et installation des dependances...
python -m pip install --upgrade pip --quiet
IF EXIST requirements.txt (
    call pip install -r requirements.txt
    IF ERRORLEVEL 1 (
        COLOR 0C
        ECHO.
        ECHO [ERREUR CRITIQUE] L'installation des dependances a echoue.
        GOTO :error_exit
    )
)

:: 3. Migrations de la base de données
ECHO.
ECHO [3/3] Execution des migrations de base de donnees...
IF EXIST migrate.py (
    call python migrate.py
    IF ERRORLEVEL 1 (
        ECHO [AVERTISSEMENT] Le script de migration a retourne un code de sortie non nul.
    )
) ELSE IF EXIST init_db.py (
    call python init_db.py
) ELSE (
    ECHO [INFO] Aucun script de migration automatique detecte.
)

:: Succès Global
COLOR 0A
ECHO.
ECHO ========================================================
ECHO    DEPLOIEMENT TERMINE AVEC SUCCES
ECHO ========================================================
GOTO :end

:error_exit
ECHO.
ECHO ========================================================
ECHO    ECHEC DU DEPLOIEMENT - INTERRUPTION DU PROCESSUS
ECHO ========================================================

:end
ECHO.
ECHO Appuyez sur une touche pour fermer cette fenetre...
PAUSE >NUL
ENDLOCAL
EXIT /B