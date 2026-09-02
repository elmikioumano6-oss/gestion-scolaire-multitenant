@echo off
title SYNCHRONISATION GESTION SCOLAIRE PRO
echo ======================================
echo SYNCHRONISATION GESTION SCOLAIRE PRO
echo ======================================
echo [1/3] Verification et recuperation des mises a jour...
git pull
echo [2/3] Preparation et sauvegarde des modifications...
git add .
git commit -m "Mise a jour et sauvegarde Gestion Scolaire Pro"
echo [3/3] Envoi sur GitHub (Mise a jour du Cloud)...
git push origin main
echo ======================================
echo OPERATION TERMINEE AVEC SUCCES !
echo ======================================
pause