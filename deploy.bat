@echo off
SETLOCAL EnableEXTENSIONS
SETLOCAL EnableDelayedExpansion

TITLE Deploiement & Workflow - Gestion Scolaire Pro
COLOR 0B

ECHO ========================================================
ECHO    GESTION SCOLAIRE PRO - WORKFLOW & DEPLOIEMENT SECURISE
ECHO ========================================================
ECHO.

:: 1. Vérification stricte de la branche locale
ECHO [1/4] Verification de l'environnement Git local...
FOR /F "tokens=*" %%i IN ('git branch --show-current') DO SET CURRENT_BRANCH=%%i

IF NOT "%CURRENT_BRANCH%"=="staging" (
    COLOR 0C
    ECHO.
    ECHO [ERREUR] Vous devez imperativement etre sur la branche 'staging'.
    ECHO Branche actuelle detectee : %CURRENT_BRANCH%
    GOTO :error_exit
)
ECHO [OK] Positionne sur 'staging'.

:: 2. Validation et publication vers le distant (main)
ECHO.
ECHO [2/4] Publication des modifications vers GitHub (main)...
git add .
:: On tente un commit, si rien n'a changé, on ignore l'erreur de commit vide
git commit -m "Mise à jour automatique staging -> main - %DATE% %TIME%" >nul 2>&1

git push origin staging:main
IF ERRORLEVEL 1 (
    COLOR 0C
    ECHO.
    ECHO [ERREUR CRITIQUE] Le push vers 'main' a ete rejete ^(conflit distant^).
    ECHO Veuillez verifier l'etat de votre depot distant.
    GOTO :error_exit
)
ECHO [OK] Modifications publiees avec succes sur 'main'.

:: 3. Mise à jour des dépendances Python
ECHO.
ECHO [3/4] Verification et mise a jour des dependances...
python -m pip install --upgrade pip --quiet
IF EXIST requirements.txt (
    call pip install -r requirements.txt
    IF ERRORLEVEL 1 (
        COLOR 0C
        ECHO [ERREUR] L'installation des dependances a echoue.
        GOTO :error_exit
    )
)

:: 4. Exécution des migrations de base de données
ECHO.
ECHO [4/4] Execution des migrations de base de donnees...
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
ECHO    DEPLOIEMENT TERMINE AVEC SUCCES ! (Vous etes sur staging)
ECHO ========================================================
GOTO :end

:error_exit
COLOR 0C
ECHO.
ECHO ========================================================
ECHO    OPERATION INTERROMPUE - SECURITE ACTIVE
ECHO ========================================================

:end
ECHO.
ECHO Appuyez sur une touche pour fermer cette fenetre...
PAUSE >NUL
ENDLOCAL
EXIT /B