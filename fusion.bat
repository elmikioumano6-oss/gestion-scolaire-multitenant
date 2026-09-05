@echo off
cls
echo ================================================
echo FUSION DU STAGING VERS LA PRODUCTION (MAIN)
echo ================================================

echo 0. Sauvegarde et validation des changements locaux sur staging...
git add .
git commit -m "chore: sauvegarde automatique avant fusion vers main"

echo 1. Passage sur la branche main...
git checkout main

echo 2. Mise a jour de main...
git pull origin main

echo 3. Fusion des modifications de staging...
git merge staging -m "Fusion du staging vers la production"

echo 4. Application des migrations de base de donnees (Alembic)...
alembic upgrade head

echo 5. Envoi de la production et de la base mise a jour sur GitHub...
git push origin main

echo.
echo ================================================
echo PRODUCTION MISE A JOUR AVEC SUCCES !
echo ================================================
pause