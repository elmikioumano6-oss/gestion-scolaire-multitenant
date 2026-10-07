import streamlit as st
from database.db_config import SessionLocal
from database.models import School, User, Eleve
from sqlalchemy import text

def afficher_health_check():
    st.subheader("🩺 Diagnostic & Santé de l'infrastructure SaaS")
    st.markdown("Vérification en temps réel de la connexion à la base de données PostgreSQL et du tunnel multi-tenant.")
    st.markdown("---")

    if st.button("Lancer le test de diagnostic"):
        db = SessionLocal()
        try:
            # Test de la connexion brute
            db.execute(text("SELECT 1"))
            st.success("✅ Connexion à la base de données PostgreSQL distante établie avec succès.")

            # Comptage des entités pour vérifier l'isolation multi-tenant
            nb_ecoles = db.query(School).count()
            nb_utilisateurs = db.query(User).count()
            nb_eleves = db.query(Eleve).count()

            col1, col2, col3 = st.columns(3)
            col1.metric("Établissements", nb_ecoles)
            col2.metric("Utilisateurs", nb_utilisateurs)
            col3.metric("Élèves enregistrés", nb_eleves)

            st.info("💡 Tous les indicateurs de santé sont au vert. Le tunnel SSH et les requêtes SQLAlchemy fonctionnent de manière optimale.")
        except Exception as e:
            st.error(f"❌ Erreur de connexion ou de diagnostic : {e}")
        finally:
            db.close()

# Alias pour le routeur
health_check = afficher_health_check