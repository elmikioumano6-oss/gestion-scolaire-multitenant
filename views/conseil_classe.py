from datetime import datetime
from io import BytesIO
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Eleve, Matiere, Note, School
from database.queries import get_classes_cached, get_matieres_cached
import pandas as pd
import streamlit as st
import unicodedata

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


def afficher_conseil_classe():
    st.subheader("🏆 Conseil de Classe & Délibérations Officielles")
    st.markdown(
        "Synthèse des résultats, attribution automatique des décisions "
        "réglementaires (Admission, Redoublement), mentions, clôture des "
        "délibérations et export Excel professionnel aux normes de "
        "l'enseignement au Niger."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    db = SessionLocal()
    try:
        if school_id:
            ecole_courante = (
                db.query(School).filter(School.id == school_id).first()
            )
            school_name = (
                ecole_courante.nom
                if ecole_courante
                else st.session_state.get("school_name", "Établissement")
            )
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

        resolved_school_id = school_id if school_id else target_school_id

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)

        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        classes_cycle = classes_query.all()

        st.markdown(f"### Conseil de Classe — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(
                f"⚠️ Aucune classe n'est actuellement configurée pour le cycle"
                f" **{cycle_en_cours}** dans l'établissement **{school_name}**."
            )
            st.info(
                "Veuillez d'abord enregistrer vos classes dans le module **Classes &"
                " Tarifs** du menu latéral."
            )
            return

        noms_classes = [c.libelle for c in classes_cycle]

        col_cc1, col_cc2 = st.columns(2)
        with col_cc1:
            classe_choisie = st.selectbox(
                "Sélectionner la classe pour les délibérations", noms_classes, key="conseil_classe_sel"
            )
        with col_cc2:
            periode_choisie = st.selectbox(
                "Période de délibération",
                [
                    "Semestre 1",
                    "Semestre 2",
                    "Trimestre 1",
                    "Trimestre 2",
                    "Trimestre 3",
                    "Annuel",
                ],
                key="conseil_periode_sel"
            )

        classe_obj = next(
            (c for c in classes_cycle if c.libelle == classe_choisie), None
        )
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            else:
                eleves_query = eleves_query.filter(
                    Eleve.school_id == target_school_id
                )
            if hasattr(Eleve, "deleted_at"):
                eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))
            eleves = eleves_query.order_by(Eleve.nom).all()

            # --- RÉCUPÉRATION EXACTE DES MATIÈRES DE LA CLASSE (Même logique que le module notes) ---
            matieres_query = db.query(Matiere).filter(
                Matiere.classe_id == classe_obj.id,
                Matiere.school_id == resolved_school_id
            )
            if hasattr(Matiere, "deleted_at"):
                matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
            matieres_classe = matieres_query.all()

            if not matieres_classe:
                st.warning(f"Aucune matière configurée pour la classe de **{classe_choisie}**.")
            elif not eleves:
                st.info(
                    f"Aucun élève enregistré dans la classe de **{classe_choisie}**."
                )
            else:
                st.success(
                    f"Délibérations en cours pour la classe de **{classe_choisie}**"
                    f" ({periode_choisie}) [{len(eleves)} élèves]."
                )

                # Récupération de l'ensemble des notes pour le calcul rigoureux basé sur les coefficients
                notes_query = (
                    db.query(Note)
                    .join(Eleve)
                    .filter(
                        Note.school_id == target_school_id,
                        Eleve.classe_id == classe_obj.id,
                    )
                )
                if periode_choisie != "Annuel":
                    notes_query = notes_query.filter(Note.semestre == periode_choisie)
                toutes_notes = notes_query.all()

                dict_coeffs = {m.id: float(getattr(m, 'coefficient', 1.0) or 1.0) for m in matieres_classe}
                stats_eleves = {}
                for e in eleves:
                    stats_eleves[e.id] = {"total_points": 0.0, "total_coeffs": 0.0}

                for n in toutes_notes:
                    if n.eleve_id in stats_eleves:
                        coeff = dict_coeffs.get(n.matiere_id, 1.0)
                        stats_eleves[n.eleve_id]["total_points"] += float(n.valeur) * coeff
                        stats_eleves[n.eleve_id]["total_coeffs"] += coeff

                synthese_data = []
                for e in eleves:
                    st_el = stats_eleves[e.id]
                    if st_el["total_coeffs"] > 0:
                        moyenne = round(st_el["total_points"] / st_el["total_coeffs"], 2)
                    else:
                        moyenne = None

                    synthese_data.append({
                        "eleve_id": e.id,
                        "Matricule": getattr(e, "matricule", "N/D"),
                        "Nom & Prénom": f"{e.nom} {e.prenom}",
                        "Moyenne": moyenne,
                        "moy_brute": moyenne if moyenne is not None else -1.0,
                    })

                # Tri par ordre de mérite décroissant
                synthese_data.sort(key=lambda x: x["moy_brute"], reverse=True)

                tableau_delib_final = []
                for idx, item in enumerate(synthese_data):
                    moy_val = item["moy_brute"]
                    rang_str = f"{idx + 1}e" if moy_val >= 0 else "En attente"
                    moy_str = f"{moy_val:.2f}" if moy_val >= 0 else "—"

                    if moy_val >= 0:
                        if moy_val >= 16:
                            mention = "Félicitations & Tableau d'Honneur"
                        elif moy_val >= 14:
                            mention = "Tableau d'Honneur (Bien)"
                        elif moy_val >= 12:
                            mention = "Encouragements (Assez Bien)"
                        elif moy_val >= 10:
                            mention = "Passable"
                        else:
                            mention = "Insuffisant"

                        if moy_val >= 10:
                            decision = "Admis(e) en classe supérieure"
                        else:
                            decision = "Redoublant(e) / Ajourné(e)"
                    else:
                        mention = "—"
                        decision = "En attente de notes"

                    tableau_delib_final.append({
                        "Rang": rang_str,
                        "Matricule": item["Matricule"],
                        "Nom & Prénom": item["Nom & Prénom"],
                        "Moyenne Générale": moy_str,
                        "Mentions & Distinctions": mention,
                        "Décision du Conseil": decision,
                    })

                df_synthese = pd.DataFrame(tableau_delib_final)
                st.dataframe(df_synthese, use_container_width=True)

                # Fonction de génération d'un fichier Excel (.xlsx) en mémoire pour un export professionnel propre
                def to_excel_buffer(df):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        df.to_excel(writer, index=False, sheet_name="Deliberations")
                    return output.getvalue()

                excel_bytes = to_excel_buffer(df_synthese)
                st.download_button(
                    label=(
                        "📥 Télécharger le Procès-Verbal officiel de Délibération"
                        " (.xlsx)"
                    ),
                    data=excel_bytes,
                    file_name=(
                        f"PV_Deliberations_{classe_choisie}_{periode_choisie.replace(' ', '')}.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ),
                )

                st.markdown("---")
                with st.form("form_cloture_conseil"):
                    st.markdown("#### 🔒 Clôture & Visa du Conseil de Classe")
                    observations_conseil = st.text_area(
                        "Remarques générales du Conseil de Classe",
                        placeholder=(
                            "Ex: Trimestre globalement satisfaisant, insister sur le"
                            " suivi des élèves en difficulté..."
                        ),
                    )
                    btn_valider = st.form_submit_button(
                        "⚖️ Valider et Clôturer les Délibérations du Conseil",
                        type="primary",
                    )

                    if btn_valider:
                        nouveau_log = ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.utcnow(),
                            username=st.session_state.get("username", "admin"),
                            action=(
                                f"Clôture des délibérations du Conseil de classe pour"
                                f" {classe_choisie} ({periode_choisie})"
                            ),
                            module="Conseil de classe",
                            statut="Validé",
                        )
                        db.add(nouveau_log)
                        db.commit()

                        st.success(
                            "✅ Les délibérations de la classe de"
                            f" **{classe_choisie}** ({periode_choisie}) ont été clôturées,"
                            " validées et archivées avec succès dans l'ERP !"
                        )
                        st.rerun()

    finally:
        db.close()


# Alias de compatibilité exhaustive pour le routeur
afficher_conseil_de_classe = afficher_conseil_classe
afficher_conseil_classe = afficher_conseil_classe