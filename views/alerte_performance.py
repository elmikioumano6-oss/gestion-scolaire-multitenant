from datetime import datetime
from io import BytesIO
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Eleve, School
import pandas as pd
import streamlit as st


def afficher_alerte_performance():
    st.subheader("🚨 Alertes de Performance & Élèves en Difficulté")
    st.markdown(
        "Détection automatique des élèves nécessitant un suivi pédagogique"
        " renforcé avec isolation multi-tenant stricte et par cycle."
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

        ecole_active_id = school_id if school_id else target_school_id

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)
        classes_cycle = classes_query.all()

        st.markdown(
            f"### Alertes de Performance — **{school_name} ({cycle_en_cours})**"
        )

        if not classes_cycle:
            st.warning(
                f"⚠️ Aucune classe disponible pour le cycle **{cycle_en_cours}** dans"
                f" l'établissement **{school_name}**."
            )
            st.info(
                "Veuillez d'abord enregistrer vos classes dans le module **Classes &"
                " Tarifs** du menu latéral."
            )
            return

        noms_classes = [c.libelle for c in classes_cycle]
        classe_choisie = st.selectbox(
            "Sélectionner la classe à auditer",
            noms_classes,
            key="alerte_classe_select",
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
            eleves = eleves_query.all()

            if not eleves:
                st.info(f"Aucun élève enregistré dans la classe **{classe_choisie}**.")
            else:
                notes_store = st.session_state.get("notes_evaluation_data", {})

                eleves_en_difficulte = []
                for e in eleves:
                    notes_eleve = []
                    for key, evaluations in notes_store.items():
                        if f"_{classe_choisie}_" in key or str(ecole_active_id) in key:
                            if e.id in evaluations:
                                notes_eleve.append(evaluations[e.id])

                    moyenne = (
                        round(sum(notes_eleve) / len(notes_eleve), 2)
                        if notes_eleve
                        else None
                    )

                    if moyenne is not None and moyenne < 10.0:
                        eleves_en_difficulte.append({
                            "Nom & Prénom": f"{e.nom} {e.prenom}",
                            "Matricule": getattr(e, "matricule", "N/D"),
                            "Moyenne Générale": f"{moyenne:.2f}",
                            "Niveau d'Alerte": "Critique (< 10/20)",
                        })

                if not eleves_en_difficulte:
                    st.success(
                        f"✅ Aucun élève en situation de difficulté critique (moyenne <"
                        f" 10) détecté dans la classe **{classe_choisie}**."
                    )
                else:
                    st.warning(
                        f"⚠️ {len(eleves_en_difficulte)} élève(s) nécessitant un suivi"
                        " pédagogique renforcé détecté(s)."
                    )
                    df_alertes = pd.DataFrame(eleves_en_difficulte)
                    st.dataframe(df_alertes, use_container_width=True)

                    # Bouton d'export officiel au format Excel (.xlsx) propre
                    def to_excel_buffer(df):
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine="openpyxl") as writer:
                            df.to_excel(writer, index=False, sheet_name="Alertes")
                        return output.getvalue()

                    excel_bytes = to_excel_buffer(df_alertes)
                    st.download_button(
                        label="📥 Télécharger le rapport des élèves en difficulté (.xlsx)",
                        data=excel_bytes,
                        file_name=(
                            f"Rapport_Alertes_Performance_{classe_choisie}.xlsx"
                        ),
                        mime=(
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        ),
                    )

            nouveau_log = ActivityLog(
                school_id=ecole_active_id,
                timestamp=datetime.utcnow(),
                username=st.session_state.get("username", "admin"),
                action=(
                    f"Consultation alertes de performance - Classe {classe_choisie}"
                ),
                module="Alerte Performance",
                statut="Succès",
            )
            db.add(nouveau_log)
            db.commit()

    finally:
        db.close()


# Alias de compatibilité
afficher_alertes_performance = afficher_alerte_performance
afficher_alerte = afficher_alerte_performance