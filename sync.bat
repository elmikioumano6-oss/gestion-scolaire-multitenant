@echo off
echo ========================================
echo SYNCHRONISATION GESTION SCOLAIRE PRO
echo ========================================

echo [1/3] Recuperation des mises a jour (git pull)...
git pull

echo [2/3] Sauvegarde des modifications (git add / commit)...
git add .
git commit -m "Mise a jour Gestion Scolaire Pro"

echo [3/3] Envoi sur le Cloud GitHub (git push)...
git push

echo ========================================
echo SYNCHRONISATION TERMINEE AVEC SUCCES !
echo ========================================
pause