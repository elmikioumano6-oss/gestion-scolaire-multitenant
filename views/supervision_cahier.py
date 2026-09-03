import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Matiere, School, ActivityLog, CahierTexte, Programme
from sqlalchemy import or_

def afficher_supervision_cahier():
    st.subheader("📋 Contrôle d'Inspection Pédagogique & Registre Officiel")
    st.markdown("Portail officiel d'audit de l'avancement des programmes, du volume horaire réel issu des programmes importés, des chapitres et de la conformité.")
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
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)
        classes_cycle = classes_query.all()

        st.markdown(f"### Supervision — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe enregistrée pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        classe_suivie = st.selectbox("Sélectionner la classe à inspecter", noms_classes)
        
        classe_obj = next((c for c in classes_cycle if c.libelle == classe_suivie), None)
        st.info(f"Registre d'inspection actif pour la classe de **{classe_suivie}** à **{school_name}**.")
        
        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        else:
            matieres_query = matieres_query.filter(Matiere.school_id == target_school_id)
        matieres_cycle = matieres_query.all()

        if not matieres_cycle or not classe_obj:
            st.info(f"Aucune matière configurée pour le cycle **{cycle_en_cours}**.")
            return

        data_suivi = []
        for mat in matieres_cycle:
            # Récupération exacte des heures prévues depuis les programmes importés (par code ou par nom)
            prog_obj = db.query(Programme).filter(
                Programme.school_id == target_school_id,
                or_(
                    Programme.code_matiere == mat.code,
                    Programme.nom_matiere == mat.libelle
                )
            ).first()
            
            heures_prevues = prog_obj.volume_horaire if prog_obj and prog_obj.volume_horaire > 0 else 0.0

            # Entrées du cahier de texte en base de données pour cette classe et cette matière
            entrees_cahier = db.query(CahierTexte).filter(
                CahierTexte.school_id == target_school_id,
                CahierTexte.classe_id == classe_obj.id,
                CahierTexte.matiere_id == mat.id
            ).all()

            # Somme exacte des durées enregistrées dans le cahier de texte
            heures_realisees = sum([float(getattr(e, 'duree', 1.0)) for e in entrees_cahier])
            
            progression_pct = round((heures_realisees / heures_prevues) * 100, 1) if heures_prevues > 0 else 0.0
            if progression_pct > 100.0:
                progression_pct = 100.0

            if entrees_cahier:
                dernier_chapitre = entrees_cahier[-1].contenu_realise[:60] + "..." if entrees_cahier[-1].contenu_realise else "N/D"
                enseignant_ref = entrees_cahier[-1].enseignant_username or "Corps professoral"
            else:
                dernier_chapitre = "Aucun cours enregistré"
                enseignant_ref = "Non assigné"

            if heures_prevues == 0.0:
                appreciation = "⚠️ Volume horaire non défini (Importez le programme)"
            elif progression_pct >= 75:
                appreciation = "🟢 Rythme excellent et conforme"
            elif progression_pct >= 40:
                appreciation = "🟡 Rythme satisfaisant"
            elif progression_pct > 0:
                appreciation = "🟠 Rythme insuffisant - Retard à rattraper"
            else:
                appreciation = "🔴 En attente de première saisie"

            data_suivi.append({
                "Matière": mat.libelle,
                "Enseignant": enseignant_ref,
                "Heures Prévues": f"{heures_prevues}h",
                "Heures Réalisées": f"{heures_realisees}h",
                "Progression (%)": f"{progression_pct}%",
                "Dernier Chapitre / Notions": dernier_chapitre,
                "Appréciation Inspecteur": appreciation
            })

        df_suivi = pd.DataFrame(data_suivi)
        st.dataframe(df_suivi, use_container_width=True)

        nouveau_log = ActivityLog(
            school_id=target_school_id,
            timestamp=datetime.now(),
            username=st.session_state.get("username", "admin"),
            action=f"Consultation registre inspection - Classe {classe_suivie}",
            module="Supervision Cahier",
            statut="Succès"
        )
        db.add(nouveau_log)
        db.commit()

    finally:
        db.close()

# Alias de compatibilité
afficher_supervision_cahier = afficher_supervision_cahier