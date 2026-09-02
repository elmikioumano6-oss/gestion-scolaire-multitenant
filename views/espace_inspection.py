import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import School, Classe, Eleve, ActivityLog

def afficher_espace_inspection():
    st.subheader("🏛️ Espace Inspection Académique & Suivi Global")
    st.markdown("Supervision institutionnelle, contrôle des effectifs et analyse comparative des performances inter-établissements.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    db = SessionLocal()
    try:
        # Restriction spécifique pour l'espace inspection (réservé aux super-admins ou rôles d'inspection)
        if not is_super_admin:
            st.warning("⚠️ Cet espace est réservé aux autorités de l'inspection académique et aux super-administrateurs.")
            return

        st.markdown(f"### Tableau de Bord Global des Établissements ({cycle_en_cours})")
        
        # Récupération de toutes les écoles de la plateforme
        ecoles = db.query(School).all()

        if not ecoles:
            st.info("Aucun établissement enregistré dans la plateforme multi-écoles.")
        else:
            data_global = []
            for ecole in ecoles:
                # Comptage des classes pour cette école et ce cycle
                nb_classes = db.query(Classe).filter(Classe.school_id == ecole.id, Classe.cycle == cycle_en_cours).count()
                
                # Comptage des élèves pour cette école et ce cycle
                classes_ids = [c.id for c in db.query(Classe).filter(Classe.school_id == ecole.id, Classe.cycle == cycle_en_cours).all()]
                nb_eleves = db.query(Eleve).filter(Eleve.school_id == ecole.id, Eleve.classe_id.in_(classes_ids)).count() if classes_ids else 0

                data_global.append({
                    "Établissement": getattr(ecole, 'nom', 'École'),
                    "Cycle Actif": cycle_en_cours,
                    "Nombre de Classes": nb_classes,
                    "Effectif Total Élèves": nb_eleves,
                    "Statut Conformité": "Conforme"
                })

            df_global = pd.DataFrame(data_global)
            st.dataframe(df_global, use_container_width=True)

            # Traçabilité dans le journal d'activité global
            target_school_id = school_id if school_id else 1
            nouveau_log = ActivityLog(
                school_id=target_school_id,
                timestamp=datetime.utcnow(),
                username=st.session_state.get("username", "super_admin"),
                action=f"Consultation du tableau de bord global d'inspection ({cycle_en_cours})",
                module="Espace Inspection",
                statut="Succès"
            )
            db.add(nouveau_log)
            db.commit()

    finally:
        db.close()

# Définition explicite des deux fonctions pour garantir la compatibilité avec le routeur app.py
def afficher_espace_inspection_academique():
    afficher_espace_inspection()