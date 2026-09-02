import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Matiere, School, ActivityLog

def afficher_supervision_progression():
    st.subheader("📚 Pilotage, Suivi & Avancement Global des Programmes")
    st.markdown("Tableau de bord exécutif de la Direction des Études : analyse croisée des volumes prévisionnels, des heures réalisées et des alertes de retard par discipline.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    
    db = SessionLocal()
    try:
        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
        else:
            school_name = st.session_state.get("school_name", "Établissement")
    finally:
        db.close()

    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # Récupération de toutes les matières du cycle actif pour l'établissement
        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        matieres_cycle = matieres_query.all()

        st.markdown(f"### Synthèse des Programmes — **{school_name} ({cycle_en_cours})**")

        if not matieres_cycle:
            st.warning(f"⚠️ Aucune matière enregistrée pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord configurer vos disciplines dans le menu **Matières & Coeffs**.")
            return

        # Récupération de toutes les entrées du cahier de texte pour ce cycle/école
        key_cahier = f"{school_id}_{cycle_en_cours}"
        toutes_entrees = st.session_state.get("cahier_texte_data", {}).get(key_cahier, [])

        data_suivi = []
        for mat in matieres_cycle:
            # Filtrage des séances dispensées pour cette matière (toutes classes confondues du cycle)
            seances_mat = [e for e in toutes_entrees if e.get("Matière") == mat.libelle]
            
            # Calcul du volume horaire réalisé (estimation standard de 2h par séance enregistrée)
            volume_realise = len(seances_mat) * 2
            
            # Volume horaire annuel prévu (standard réglementaire de 45h)
            volume_prevu = 45 
            
            # Calcul du taux de couverture
            taux = min(100, int((volume_realise / volume_prevu) * 100)) if volume_prevu > 0 else 0

            # Analyse croisée et attribution de la remarque / statut de retard
            if taux < 20:
                remarque = "🔴 En retard critique"
            elif taux < 40:
                remarque = "🟠 En léger retard"
            elif taux <= 80:
                remarque = "🟢 Rythme conforme"
            else:
                remarque = "🔵 Programme bien avancé"

            data_suivi.append({
                "Discipline / Matière": mat.libelle,
                "Coefficient": getattr(mat, 'coefficient', 1) or 1,
                "Volume Prévu": f"{volume_prevu}h",
                "Volume Réalisé": f"{volume_realise}h",
                "Taux d'Avancement": f"{taux}%",
                "Analyse & Remarque": remarque
            })

        df_suivi = pd.DataFrame(data_suivi)
        st.dataframe(df_suivi, use_container_width=True)

        # Traçabilité de l'audit dans le journal d'activité
        target_school_id = school_id or 1
        db.add(ActivityLog(
            school_id=target_school_id,
            timestamp=datetime.utcnow(),
            username=st.session_state.get("username", "admin"),
            action=f"Consultation du suivi global des programmes ({cycle_en_cours})",
            module="Suivi des Programmes",
            statut="Succès"
        ))
        db.commit()

    finally:
        db.close()

# Alias de compatibilité exhaustive pour éviter toute erreur du routeur app.py
afficher_suivi_programmes = afficher_supervision_progression
afficher_suivi_des_programmes = afficher_supervision_progression