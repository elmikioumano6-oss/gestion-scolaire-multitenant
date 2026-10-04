@echo off
SETLOCAL EnableEXTENSIONS
SETLOCAL EnableDelayedExpansion

TITLE Deploiement - Gestion Scolaire Pro [Staging vers Main]
COLOR 0B

ECHO ========================================================
ECHO    DEPLOIEMENT AUTOMATISE - GESTION SCOLAIRE PRO
ECHO ========================================================
ECHO.

:: 0. Envoi des modifications de la branche locale staging vers main sur le distant
ECHO [0/3] Envoi des modifications locales vers GitHub (branche distante main)...
call git add .
call git commit -m "Mise à jour automatique staging -> main - %DATE% %TIME%"
call git push origin staging:main
IF ERRORLEVEL 1 (
    ECHO [INFO] Aucun nouveau changement à commiter ou synchronisation déjà à jour.
)

:: 1. Synchronisation Git locale (retour sur staging et pull)
ECHO.
ECHO [1/3] Synchronisation du code source (GitHub - staging)...
call git checkout staging 2>nul
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