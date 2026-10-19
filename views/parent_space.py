from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import (
    Classe,
    Eleve,
    EmploiDuTemps,
    Matiere,
    Note,
    Paiement,
    Presence,
    School,
    User,
    Message,
)
import pandas as pd
import streamlit as st


def afficher_espace_parent():
    st.markdown("""
        <style>
        .student-card {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }
        .student-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .student-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #e2e8f0; }
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            background-color: rgba(255,255,255,0.03);
            border-radius: 12px;
            color: #a0aec0;
            border: 1px dashed rgba(255,255,255,0.2);
            margin-top: 15px;
        }
        .empty-state h4 { color: #e2e8f0; margin-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 👋 Bienvenue dans votre Espace Famille")
    st.markdown("Suivez la scolarité, l'assiduité et la situation financière de vos enfants en temps réel.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
    username = st.session_state.get("username")
    user_role = st.session_state.get("role", "")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        user_obj = db.query(User).filter(User.username == username).first() if username else None

        eleves_query = db.query(Eleve).filter(Eleve.deleted_at.is_(None))

        if user_role and user_role.lower() == "parent" and user_obj:
            # Récupérer tous les élèves liés à ce parent (via parent_id ou eleve_id)
            eleves_query = eleves_query.filter(
                (Eleve.parent_id == user_obj.id) | (Eleve.id == user_obj.eleve_id)
            )
        else:
            classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
            if not is_super_admin and school_id:
                classes_query = classes_query.filter(Classe.school_id == school_id)
            classes_cycle = classes_query.all()
            classes_ids = [c.id for c in classes_cycle]

            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            if classes_ids:
                eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))
            else:
                eleves_query = eleves_query.filter(Eleve.classe_id == -1)

        eleves = eleves_query.all()

        if not eleves:
            if user_role and user_role.lower() == "parent":
                st.warning("⚠️ Aucun profil d'élève n'est actuellement rattaché à votre compte parent.")
            else:
                st.info(f"📌 Aucun élève enregistré pour le cycle **{cycle_en_cours}**.")
        else:
            noms_names = [f"{e.nom} {e.prenom} (Matricule: {e.matricule})" for e in eleves]
            eleve_choisi = st.selectbox("👨‍👩‍👧‍👦 Sélectionner l'enfant à consulter", noms_names)

            eleve_obj = next(
                (e for e in eleves if f"{e.nom} {e.prenom} (Matricule: {e.matricule})" == eleve_choisi),
                None,
            )

            if eleve_obj:
                classe = db.query(Classe).filter(Classe.id == eleve_obj.classe_id).first() if eleve_obj.classe_id else None
                classe_nom = classe.libelle if classe and hasattr(classe, "libelle") and classe.libelle else getattr(classe, "nom", "Non assignée")

                notes_list = db.query(Note).filter(Note.eleve_id == eleve_obj.id).all()
                moy_str = "N/A"
                if notes_list:
                    moy_calc = sum(float(n.valeur) for n in notes_list) / len(notes_list)
                    moy_str = f"{moy_calc:.2f} / 20"

                presences_list = db.query(Presence).filter(Presence.eleve_id == eleve_obj.id).all()
                nb_absences = sum(1 for p in presences_list if "Absent" in str(p.statut))
                nb_retards = sum(1 for p in presences_list if "Retard" in str(p.statut))

                frais_scol = float(getattr(classe, "frais_scolarite", 0.0) or 0.0) if classe else 0.0
                frais_inscr = float(getattr(classe, "frais_inscription", 0.0) or 0.0) if classe else 0.0
                frais_coges = float(getattr(classe, "frais_coges", 0.0) or 0.0) if classe else 0.0
                montant_brut = (frais_scol + frais_inscr + frais_coges) if (frais_scol + frais_inscr + frais_coges) > 0 else 65000.0
                reduction = float(getattr(eleve_obj, "montant_reduction", 0.0) or 0.0)
                montant_du_net = max(0.0, montant_brut - reduction)
                paiements_eleve = db.query(Paiement).filter(Paiement.eleve_id == eleve_obj.id).all()
                montant_paye = sum(float(p.montant) for p in paiements_eleve) if paiements_eleve else 0.0
                solde_restant = montant_du_net - montant_paye
                statut_finance = "À jour ✅" if solde_restant <= 0 else "Impayé ⚠️"

                st.markdown(f"""
                    <div class="student-card">
                        <div style="font-size: 3.5rem; margin-right: 25px;">🎓</div>
                        <div>
                            <h2>{eleve_obj.nom} {eleve_obj.prenom}</h2>
                            <p>Classe : <b>{classe_nom}</b> &nbsp;|&nbsp; Cycle : {cycle_en_cours} &nbsp;|&nbsp; Matricule : {eleve_obj.matricule}</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                col_k1, col_k2, col_k3, col_k4 = st.columns(4)
                with col_k1:
                    st.metric("Moyenne (Est.)", moy_str)
                with col_k2:
                    st.metric("Absences", f"{nb_absences}")
                with col_k3:
                    st.metric("Retards", f"{nb_retards}")
                with col_k4:
                    st.metric("Situation Financière", statut_finance)

                st.markdown("<br>", unsafe_allow_html=True)

                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                    "📚 Notes & Évaluations",
                    "📋 Bulletins",
                    "🕒 Emploi du Temps",
                    "📌 Assiduité",
                    "💳 Situation Financière",
                    "✉️ Message",
                ])

                with tab1:
                    st.markdown("#### Notes des Évaluations Récentes")
                    if not notes_list:
                        st.info("Aucune note enregistrée.")
                    else:
                        data_notes = []
                        for n in notes_list:
                            mat = db.query(Matiere).filter(Matiere.id == n.matiere_id).first()
                            mat_lib = mat.libelle if mat and hasattr(mat, "libelle") and mat