from datetime import datetime
from io import BytesIO
from database.db_config import SessionLocal
from database.models import ActivityLog, AnneeScolaire, Classe, Eleve, Matiere, Note, School
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import unicodedata

# Dictionnaire de correspondance universel pour unifier les synonymes de matières
SYNONYMES_MATIERES = {
    "sciences physiques": "physique chimie",
    "physique chimie": "physique chimie",
    "svt": "science de la vie et de la terre",
    "science de la vie et de la terre": "science de la vie et de la terre",
    "eps": "education physique et sportive",
    "education physique et sportive": "education physique et sportive",
    "economie familiale": "economie familiale et sociale",
    "economie familiale et sociale": "economie familiale et sociale",
    "histoire geographie": "histoire geographie",
    "histoire-geographie": "histoire geographie",
}

def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    nettoye = " ".join(sans_accent.lower().replace("-", " ").replace("_", " ").split())
    return SYNONYMES_MATIERES.get(nettoye, nettoye)

def afficher_consultation_notes():
    st.markdown(
        """
    <style>
        @media print {
            body { background-color: white !important; color: black !important; }
            .stButton, .stSelectbox, sidebar, header, footer, [data-testid="stSidebar"] { display: none !important; }
            .printable-area { width: 100% !important; padding: 10px !important; margin: 0 !important; }
            .print-footer { position: fixed; bottom: 0; left: 0; right: 0; text-align: center; font-size: 8pt; border-top: 1px solid #ccc; padding-top: 8px; color: #333; background-color: white; }
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.subheader("📊 Consultation Détaillée des Notes & Résultats")
    st.markdown("Recherche et affichage dynamique des notes par évaluation, ou des moyennes par semestre et annuelle.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    db = SessionLocal()
    try:
        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
            school_devise = ecole_courante.devise if ecole_courante else "Excellence - Persévérance - Réussite"
            school_adresse = ecole_courante.adresse if ecole_courante and ecole_courante.adresse else "Niamey - Niger"
            school_contacts = ecole_courante.contacts if ecole_courante and ecole_courante.contacts else "N/D"
        else:
            school_name = st.session_state.get("school_name", "Établissement")
            school_devise = "Excellence - Persévérance - Réussite"
            school_adresse = "Niamey - Niger"
            school_contacts = "N/D"

        annee_active = db.query(AnneeScolaire).filter(AnneeScolaire.school_id == school_id, AnneeScolaire.active == True).first()
        libelle_annee = annee_active.libelle if annee_active else str(datetime.now().year)
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
        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)

        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == target_school_id)

        classes_cycle = classes_query.all()
        matieres_brutes = matieres_query.all()

        # DÉDUPLICATION INTELLIGENTE DES MATIÈRES VIA LE DICTIONNAIRE DE SYNONYMES
        matieres_uniques_dict = {}
        for mat in matieres_brutes:
            nom_brut = mat.libelle if hasattr(mat, 'libelle') and mat.libelle else getattr(mat, 'nom', 'Matière')
            norm_key = normaliser_chaine(nom_brut)
            if norm_key not in matieres_uniques_dict:
                matieres_uniques_dict[norm_key] = mat
        matieres_cycle = list(matieres_uniques_dict.values())

        st.markdown('<div class="printable-area">', unsafe_allow_html=True)
        st.markdown(f"### Consultation des Notes ({libelle_annee}) — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe disponible pour le cycle **{cycle_en_cours}**.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        noms_classes = [c.libelle for c in classes_cycle]

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            classe_choisie = st.selectbox("Sélectionner la classe", noms_classes, key="consult_notes_classe")
        with col_c2:
            semestre_choisi = st.selectbox("Semestre / Période", ["Semestre 1", "Semestre 2", "Trimestre 1", "Trimestre 2", "Trimestre 3"], key="consult_notes_semestre")
        with col_c3:
            type_vue = st.selectbox("Type d'affichage / Évaluation", ["Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo", "Moyen-S1", "Moyen-S2", "Moyen-an"], key="consult_notes_vue")

        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            else:
                eleves_query = eleves_query.filter(Eleve.school_id == target_school_id)
            eleves = eleves_query.order_by(Eleve.nom).all()

            if not eleves:
                st.info(f"Aucun élève enregistré dans la classe de **{classe_choisie}**.")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.success(f"Résultats affichés pour la classe de **{classe_choisie}** — Vue : **{type_vue}** ({semestre_choisi}) [{len(eleves)} élèves].")

                if type_vue in ["Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo"]:
                    notes_db = db.query(Note).join(Eleve).filter(
                        Note.school_id == target_school_id,
                        Eleve.classe_id == classe_obj.id,
                        Note.semestre == semestre_choisi,
                        Note.type_evaluation == type_vue,
                    ).all()

                    dict_notes = {(n.eleve_id, n.matiere_id): float(n.valeur) for n in notes_db if n.valeur is not None}
                    dict_coeffs = {m.id: (m.coefficient or 1.0) for m in matieres_cycle}

                    data_tableau = []
                    for e in eleves:
                        sexe_eleve = str(getattr(e, "sexe", "M")).strip().upper()
                        ligne = {"Matricule": e.matricule, "Nom & Prénom": f"{e.nom} {e.prenom}", "_sexe": sexe_eleve}
                        total_pts = 0.0
                        total_coefs = 0.0

                        for mat in matieres_cycle:
                            mat_lib = (mat.libelle if hasattr(mat, 'libelle') else getattr(mat, 'nom', '')).title()
                            val_note = dict_notes.get((e.id, mat.id), 0.0)
                            ligne[mat_lib] = f"{val_note:.2f}"
                            c_val = dict_coeffs.get(mat.id, 1.0)
                            total_pts += val_note * c_val
                            total_coefs += c_val

                        moy_val = round(total_pts / total_coefs, 2) if total_coefs > 0 else 0.0
                        ligne["_moy_val"] = moy_val
                        ligne["Moyenne"] = f"{moy_val:.2f}/20"
                        data_tableau.append(ligne)

                    data_tableau = sorted(data_tableau, key=lambda x: x["_moy_val"], reverse=True)
                    for r_idx, item in enumerate(data_tableau, start=1):
                        sexe_val = item.get("_sexe", "M")
                        is_feminin = sexe_val in ["F", "FÉMININ", "FEMININ", "FILLE"]
                        if r_idx == 1:
                            item["Rang"] = "1ère" if is_feminin else "1er"
                        else:
                            item["Rang"] = f"{r_idx}ème" if is_feminin else f"{r_idx}è"
                        item.pop("_moy_val", None)
                        item.pop("_sexe", None)

                    df_res = pd.DataFrame(data_tableau)
                    st.dataframe(df_res, use_container_width=True)

                    # --- SECTION DE SUPPRESSION CIBLÉE DES NOTES D'ESSAI ---
                    st.markdown("---")
                    st.markdown("#### 🗑️ Supprimer une note ou réinitialiser une évaluation")
                    notes_a_supprimer = db.query(Note).join(Eleve).filter(
                        Note.school_id == target_school_id,
                        Eleve.classe_id == classe_obj.id,
                        Note.semestre == semestre_choisi,
                        Note.type_evaluation == type_vue
                    ).all()

                    if notes_a_supprimer:
                        options_notes = {
                            f"Élève ID {n.eleve_id} — Matière ID {n.matiere_id} — Valeur : {n.valeur} ({n.type_evaluation})": n.id
                            for n in notes_a_supprimer
                        }
                        note_selectionnee_label = st.selectbox("Sélectionner la note spécifique à supprimer", list(options_notes.keys()), key="select_suppr_note")
                        if st.button("🗑️ Supprimer cette note", type="secondary"):
                            id_note_del = options_notes[note_selectionnee_label]
                            note_obj_del = db.query(Note).filter(Note.id == id_note_del).first()
                            if note_obj_del:
                                db.delete(note_obj_del)
                                db.commit()
                                st.success("✅ Note supprimée avec succès !")
                                st.rerun()
                    else:
                        st.info("Aucune note enregistrée pour cette période/évaluation.")

                else:
                    st.info("Sélectionnez une évaluation (Interro, Devoir, Compo) pour consulter le détail par matière.")

        st.markdown("</div>", unsafe_allow_html=True)
    finally:
        db.close()

afficher_consultation_notes = afficher_consultation_notes
afficher_consultation_des_notes = afficher_consultation_notes
afficher_consultations_notes = afficher_consultation_notes