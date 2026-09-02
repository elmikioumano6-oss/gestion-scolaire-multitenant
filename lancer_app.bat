@echo off
cd /d "%~dp0"
echo ========================================================
echo   Lancement de Gestion Scolaire Pro (Plateforme Multi-Tenant)
echo ========================================================
echo Activation de l'environnement ou lancement direct de Streamlit...
streamlit run app.py
pause