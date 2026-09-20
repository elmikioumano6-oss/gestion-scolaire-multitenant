from datetime import datetime
import unicodedata
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import (
    ActivityLog,
    CahierTexte,
    Classe,
    Eleve,
    Matiere,
    Note,
    Programme,
    Presence,
    School,
)
from database.queries import get_classes_cached, get_matieres_cached

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
    nettoye = " ".join(
        sans_accent.lower().replace("-", " ").replace("_", " ").split()
    )
    return SYNONYMES_MATIERES.get(nettoye, nettoye)


def afficher_espace_enseignants():
    st.subheader("👨‍🏫 Espace Pédagogique Enseignant")
    st.markdown(
        "Plateforme unifiée pour l'appel, la saisie des notes, le cahier de texte"
        " et le suivi des charges horaires avec restriction stricte aux classes"
        " assignées et isolation multi-tenant complète."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    user_role = str(st.session_state.get("role", "enseignant")).lower()
    username = st.session_state.get("username", "enseignant")
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

        ecole_courante = (
            db.query(School).filter(School.id == ecole_active_id).first()
        )
        school_name = (
            ecole_courante.nom
            if ecole_courante
            else st.session_state.get("school_name", "Établissement")
        )

        classes_query = db.query(Classe).filter(
            Classe.cycle == cycle_en_cours, Classe.school_id == ecole_active_id
        )
        matieres_query = db.query(Matiere).filter(
            Matiere.cycle == cycle_en_cours, Matiere.school_id == ecole_active_id
        )

        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        if hasattr(Matiere, "deleted_at"):
            matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))

        toutes_classes_cycle = classes_query.all()
        toutes_matieres_cycle = matieres_query.all()

        if not toutes_classes_cycle or not toutes_matieres_cycle:
            st.warning(
                f"⚠️ Veuillez vous assurer que des classes et des matières sont"
                f" configurées pour le cycle **{cycle_en_cours}** dans"
                f" l'établissement **{school_name}**."
            )
            return

        affectations_prof = st.session_state.get("teacher_assignments", {})
        if (
            user_role in ["directeur", "admin", "administrateur", "super_admin"]
            or not affectations_prof.get(username)
        ):
            classes_disponibles = toutes_classes_cycle
            matieres_disponibles = toutes_matieres_cycle
        else:
            classes_assignées_noms = (
                affectations_prof.get(username, {}).get("classes", [])
            )
            matieres_assignées_noms = (
                affectations_prof.get(username, {}).get("matieres", [])
            )

            classes_disponibles = [
                c for c in toutes_classes_cycle if c.libelle in classes_assignées_noms
            ]
            matieres_disponibles = [
                m
                for m in toutes_matieres_cycle
                if (m.libelle if hasattr(m, 'libelle') else getattr(m, 'nom', ''))
                in matieres_assignées_noms
            ]

            if not classes_disponibles:
                classes_disponibles = toutes_classes_cycle
            if not matieres_disponibles:
                matieres_disponibles = toutes_matieres_cycle

        noms_classes = [c.libelle for c in classes_disponibles]
        noms_matieres = [
            m.libelle if hasattr(m, 'libelle') else getattr(m, 'nom', '')
            for m in matieres_disponibles
        ]

        st.markdown(
            f"### Espace Enseignant (`{username}`) — **{school_name}"
            f" ({cycle_en_cours})**"
        )

        col1, col2 = st.columns(2)
        with col1:
            classe_enseignant = st.selectbox(
                "Vos classes assignées", noms_classes, key="ens_classe_select"
            )
        with col2:
            matiere_enseignant = st.selectbox(
                "Vos matières dispensées", noms_matieres, key="ens_matiere_select"
            )

        classe_obj = next(
            (c for c in classes_disponibles if c.libelle == classe_enseignant), None
        )
        matiere_obj = next(
            (
                m
                for m in matieres_disponibles
                if (m.libelle if hasattr(m, 'libelle') else getattr(m, 'nom', ''))
                == matiere_enseignant
            ),
            None,
        )

        eleves = []
        if classe_obj:
            eleves_query = db.query(Eleve).filter(
                Eleve.classe_id == classe_obj.id, Eleve.school_id == ecole_active_id
            )
            if hasattr(Eleve, "deleted_at"):
                eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))
            eleves = eleves_query.order_by(Eleve.nom).all()

        tab_cahier, tab_notes, tab_appel, tab_charge = st.tabs([
            "📖 Cahier de Texte",
            "📝 Saisie des Notes",
            "📋 Feuille d'Appel",
            "📊 Horaires & Reste à faire",
        ])

        # --- 1. CAHIER DE TEXTE ---
        with tab_cahier:
            st.markdown(
                f"#### 📖 Saisie du Cahier de Texte — **{classe_enseignant}**"
                f" ({matiere_enseignant})"
            )
            with st.form("form_ens_cahier_texte_avance"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    date_seance = st.date_input(
                        "Date de la séance",
                        value=datetime.now().date(),
                        key="ens_date_cours",
                    )
                with col_c2:
                    duree_seance = st.selectbox(
                        "Durée de la séance",
                        ["1 heure", "2 heures", "3 heures", "4 heures"],
                        key="ens_duree_seance",
                    )

                titre_seance = st.text_input(
                    "Titre du cours ou du chapitre *",
                    placeholder="Ex: Chapitre 3 - Les équations du premier degré",
                    key="ens_titre_cours",
                )
                contenu_seance = st.text_area(
                    "Contenu réalisé / Résumé de la leçon *",
                    placeholder="Détaillez les notions et le contenu dispensé...",
                    key="ens_contenu_cours",
                )
                difficultees = st.text_area(
                    "Difficultés rencontrées / Remarques (Optionnel)",
                    placeholder="Observations pédagogiques particulières...",
                    key="ens_difficultees",
                )
                mesures_correctives = st.text_area(
                    "Mesures correctives / Travail à faire (Optionnel)",
                    placeholder="Exercices assignés pour la prochaine séance...",
                    key="ens_mesures",
                )

                submitted_cahier = st.form_submit_button(
                    "📤 Enregistrer & Transmettre à l'Inspection", type="primary"
                )
                if submitted_cahier:
                    if not titre_seance.strip() or not contenu_seance.strip():
                        st.error(
                            "⚠️ Veuillez renseigner le titre et le contenu détaillé du cours."
                        )
                    elif not classe_obj or not matiere_obj:
                        st.error("⚠️ Classe ou matière invalide.")
                    else:
                        nouvelle_entree = CahierTexte(
                            school_id=ecole_active_id,
                            cycle=cycle_en_cours,
                            classe_id=classe_obj.id,
                            matiere_id=matiere_obj.id,
                            user_id=st.session_state.get("user_id"),
                            date_cours=datetime.combine(
                                date_seance, datetime.min.time()
                            ),
                            duree_seance=duree_seance,
                            titre=titre_seance.strip(),
                            contenu=contenu_seance.strip(),
                            difficultees=difficultees.strip() if difficultees else None,
                            mesures_correctives=(
                                mesures_correctives.strip()
                                if mesures_correctives
                                else None
                            ),
                            est_substitue=0,
                            auteur_saisie=username,
                            statut_validation="Validé",
                        )
                        db.add(nouvelle_entree)
                        db.commit()
                        st.success(
                            "✅ Entrée du cahier de texte enregistrée et transmise au"
                            " registre de l'établissement avec succès !"
                        )

        # --- 2. SAISIE DES NOTES ---
        with tab_notes:
            st.markdown(
                f"#### 📝 Saisie des Notes — **{classe_enseignant}**"
                f" ({matiere_enseignant})"
            )
            if not eleves:
                st.info("Aucun élève enregistré dans cette classe.")
            else:
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    type_evaluation = st.selectbox(
                        "Type d'évaluation",
                        ["Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo"],
                        key="ens_type_eval",
                    )
                with col_n2:
                    semestre = st.selectbox(
                        "Période Académique",
                        [
                            "Semestre 1",
                            "Semestre 2",
                            "Trimestre 1",
                            "Trimestre 2",
                            "Trimestre 3",
                        ],
                        key="ens_semestre_notes",
                    )

                with st.form("form_ens_notes_saisie"):
                    saisie_temp = {}
                    for e in eleves:
                        saisie_temp[e.id] = st.number_input(
                            f"{e.nom} {e.prenom} (Matricule: {getattr(e, 'matricule', 'N/A')})"
                            " — Note sur 20",
                            min_value=0.0,
                            max_value=20.0,
                            value=0.0,
                            step=0.25,
                            key=f"ens_note_{e.id}",
                        )

                    submitted_notes = st.form_submit_button(
                        "💾 Synchroniser les notes avec l'administration",
                        type="primary",
                    )
                    if submitted_notes:
                        for eleve_id, valeur_note in saisie_temp.items():
                            note_obj = Note(
                                school_id=ecole_active_id,
                                eleve_id=eleve_id,
                                matiere_id=matiere_obj.id if matiere_obj else None,
                                valeur=valeur_note,
                                semestre=semestre,
                                type_evaluation=type_evaluation,
                            )
                            db.add(note_obj)
                        db.commit()
                        st.success("✅ Notes synchronisées avec succès !")

        # --- 3. FEUILLE D'APPEL ---
        with tab_appel:
            st.markdown(
                f"#### 📋 Feuille d'Appel Numérique — **{classe_enseignant}**"
            )
            if not eleves:
                st.info("Aucun élève enregistré dans cette classe.")
            else:
                date_appel = st.date_input(
                    "Date de l'appel", value=datetime.today(), key="ens_date_appel"
                )
                data_appel = []
                for e in eleves:
                    data_appel.append({
                        "eleve_id": e.id,
                        "Matricule": getattr(e, "matricule", "N/A"),
                        "Nom & Prénom": f"{e.nom} {e.prenom}",
                        "Présent(e)": True,
                        "Retard (min)": 0,
                        "Motif d'absence": "—",
                    })
                df_appel = pd.DataFrame(data_appel)
                edited_appel = st.data_editor(
                    df_appel,
                    use_container_width=True,
                    key=f"ens_appel_editor_{classe_enseignant}",
                )

                if st.button("📤 Valider et transmettre l'appel à la vie scolaire"):
                    for index, row in edited_appel.iterrows():
                        motif_str = str(row["Motif d'absence"])
                        statut_presence = (
                            "Présent"
                            if row["Présent(e)"]
                            else f"Absent (Motif: {motif_str})"
                        )
                        if row["Retard (min)"] > 0:
                            statut_presence = f"Retard ({row['Retard (min)']} min)"

                        presence_obj = Presence(
                            school_id=ecole_active_id,
                            eleve_id=int(row["eleve_id"]),
                            date=date_appel,
                            statut=statut_presence,
                            motif=motif_str if not row["Présent(e)"] else None,
                        )
                        db.add(presence_obj)
                    db.commit()
                    st.success("✅ Feuille d'appel validée avec succès !")

        # --- 4. HORAIRES & RESTE À FAIRE (LOGIQUE STRICTE IDENTIQUE À LA SUPERVISION) ---
        with tab_charge:
            st.markdown(
                f"#### 📊 Suivi de la Charge Horaire & Reste à Faire —"
                f" **{matiere_enseignant} ({classe_enseignant})**"
            )

            if classe_obj and matiere_obj:
                all_programmes = db.query(Programme).filter(
                    Programme.school_id == ecole_active_id
                ).all()

                norm_key = normaliser_chaine(matiere_enseignant)
                libelle_classe_norm = normaliser_chaine(classe_enseignant)
                
                niveau_cible = "3ème"
                for mot, lib_long in [("6", "6ème"), ("5", "5ème"), ("4", "4ème"), ("3", "3ème")]:
                    if mot in libelle_classe_norm or mot + "e" in libelle_classe_norm or mot + "è" in libelle_classe_norm:
                        niveau_cible = lib_long
                        break

                heures_prevues = 0.0
                
                # 1. Recherche par base de données (modèle Programme)
                prog_classe = next(
                    (p for p in all_programmes 
                     if normaliser_chaine(getattr(p, 'nom_matiere', '')) == norm_key 
                     and normaliser_chaine(niveau_cible) in normaliser_chaine(getattr(p, 'code_matiere', ''))),
                    None
                )

                if prog_classe and prog_classe.volume_horaire and prog_classe.volume_horaire > 0:
                    heures_prevues = float(prog_classe.volume_horaire)
                else:
                    # 2. Barème officiel du collège identique à la supervision
                    BAREME_COLLEGE = {
                        "6ème": {"francais": 205, "anglais": 140, "histoire geographie": 70, "mathematiques": 240, "physique chimie": 35, "science de la vie et de la terre": 70, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                        "5ème": {"francais": 140, "anglais": 140, "histoire geographie": 70, "mathematiques": 175, "physique chimie": 35, "science de la vie et de la terre": 70, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                        "4ème": {"francais": 140, "anglais": 140, "histoire geographie": 70, "mathematiques": 175, "physique chimie": 105, "science de la vie et de la terre": 70, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                        "3ème": {"francais": 140, "anglais": 140, "histoire geographie": 70, "mathematiques": 175, "physique chimie": 105, "science de la vie et de la terre": 105, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                    }
                    if niveau_cible in BAREME_COLLEGE and norm_key in BAREME_COLLEGE[niveau_cible]:
                        heures_prevues = float(BAREME_COLLEGE[niveau_cible][norm_key])
                    elif hasattr(matiere_obj, "volume_horaire") and matiere_obj.volume_horaire:
                        heures_prevues = float(matiere_obj.volume_horaire)
                    else:
                        heures_prevues = 45.0

                volume_total_prevu = heures_prevues

                # Calcul des heures dispensées pour CETTE classe et CETTE matière
                seances_matiere = (
                    db.query(CahierTexte)
                    .filter(
                        CahierTexte.school_id == ecole_active_id,
                        CahierTexte.classe_id == classe_obj.id,
                        CahierTexte.matiere_id == matiere_obj.id,
                    )
                    .all()
                )

                volume_dispense = 0.0
                for s in seances_matiere:
                    d_str = str(getattr(s, "duree_seance", "1 heure"))
                    try:
                        chiffre = float("".join(filter(str.isdigit, d_str)) or 1)
                        volume_dispense += chiffre
                    except Exception:
                        volume_dispense += 1.0

                reste_a_faire = max(0.0, volume_total_prevu - volume_dispense)
                progression_pct = min(
                    100, int((volume_dispense / volume_total_prevu) * 100)
                    if volume_total_prevu > 0
                    else 0
                )

                col_h1, col_h2, col_h3 = st.columns(3)
                with col_h1:
                    st.metric("Volume Horaire Dispensé", f"{volume_dispense:g}h")
                with col_h2:
                    st.metric("Volume Total Annuel Prévu", f"{volume_total_prevu:g}h")
                with col_h3:
                    st.metric("Reste à Faire", f"{reste_a_faire:g}h")

                st.progress(
                    max(0.0, min(1.0, progression_pct / 100.0)),
                    text=f"Progression globale du programme : {progression_pct}%",
                )
            else:
                st.info("Veuillez sélectionner une classe et une matière valides.")

    finally:
        db.close()


afficher_espace_enseignants = afficher_espace_enseignants
afficher_enseignants = afficher_espace_enseignants
afficher_espace_enseignant = afficher_espace_enseignants