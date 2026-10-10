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
    Enseignant,
    Matiere,
    Note,
    Programme,
    Presence,
    School,
    User,
)

SYNONYMES_MATIERES = {
    "sciences physiques": "physique chimie",
    "physique chimie": "physique chimie",
    "svt": "science de la vie et de la terre",
    "science de la vie et de la terre": "science de la vie et de la terre",
    "eps": "eps",
    "education physique": "eps",
    "education physique et sportive": "eps",
    "economie familiale": "economie familiale et sociale",
    "economie familiale et sociale": "economie familiale et sociale",
    "economie familiale sociale": "economie familiale et sociale",
    "histoire geographie": "histoire geographie",
    "histoire-geographie": "histoire geographie",
    "education civique": "education civique et morale",
    "education civique et morale": "education civique et morale",
    "education civique morale": "education civique et morale",
    "conduite": "conduite",
}


def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    nettoye = " ".join(sans_accent.lower().replace("-", " ").replace("_", " ").replace("è", "e").replace("é", " e").split())
    return SYNONYMES_MATIERES.get(nettoye, nettoye)


def get_matieres_classe_strict(classe_obj, ecole_active_id, db, enseignant_obj=None):
    if not classe_obj:
        return []
    try:
        matieres_autorisees = []
        if enseignant_obj and hasattr(enseignant_obj, "matieres_attribuees") and enseignant_obj.matieres_attribuees:
            matieres_autorisees = [m.strip().title() for m in enseignant_obj.matieres_attribuees.split(",") if m.strip()]

        mat_q = db.query(Matiere).filter(
            Matiere.school_id == ecole_active_id,
            Matiere.classe_id == classe_obj.id
        )
        if hasattr(Matiere, "deleted_at"):
            mat_q = mat_q.filter(Matiere.deleted_at.is_(None))
        matieres_brutes = mat_q.all()
        
        if not matieres_brutes:
            mat_all_q = db.query(Matiere).filter(Matiere.school_id == ecole_active_id)
            if hasattr(Matiere, "deleted_at"):
                mat_all_q = mat_all_q.filter(Matiere.deleted_at.is_(None))
            matieres_brutes = mat_all_q.all()

        noms = []
        for m in matieres_brutes:
            nom_m = m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "Matière")
            if nom_m:
                titre_m = nom_m.title()
                if not matieres_autorisees or any(m_auth.lower() in titre_m.lower() or titre_m.lower() in m_auth.lower() for m_auth in matieres_autorisees):
                    noms.append(titre_m)

        if not noms and matieres_autorisees:
            noms = matieres_autorisees

        return sorted(list(set(noms))) if noms else ["Matière Générale"]
    except Exception:
        return ["Matière Générale"]


def afficher_espace_enseignants():
    st.markdown("""
        <style>
        .teacher-card {
            background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
        }
        .teacher-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .teacher-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #e2e8f0; }
        .context-box {
            background-color: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px 20px 5px 20px;
            margin-bottom: 25px;
        }
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
        .tab-title {
            color: #4da6ff;
            font-weight: 600;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 👨‍🏫 Espace Pédagogique Enseignant")
    st.markdown("Plateforme unifiée pour l'appel, la saisie des notes, le cahier de texte et le suivi des charges horaires.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    user_role = str(st.session_state.get("role", "enseignant")).lower()
    username = st.session_state.get("username", "enseignant")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège / Lycée")

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
        ecole_courante = db.query(School).filter(School.id == ecole_active_id).first()
        school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")

        user_obj = db.query(User).filter(User.username == username).first() if username else None
        enseignant_obj = None
        if user_obj and hasattr(user_obj, "enseignant_id") and user_obj.enseignant_id:
            enseignant_obj = db.query(Enseignant).filter(Enseignant.id == user_obj.enseignant_id).first()

        classes_query = db.query(Classe).filter(Classe.school_id == ecole_active_id)
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        toutes_classes_ecole = classes_query.all()

        if not toutes_classes_ecole:
            st.warning(f"⚠️ Veuillez vous assurer que des classes sont configurées dans l'établissement **{school_name}**.")
            return

        if user_role in ["directeur", "admin", "administrateur", "super_admin", "censeur"] or not enseignant_obj:
            classes_disponibles = toutes_classes_ecole
        else:
            classes_str = getattr(enseignant_obj, "classes_attribuees", "") or getattr(enseignant_obj, "classes", "") or ""
            classes_prof = [c.strip().lower() for c in classes_str.split(",") if c.strip()]
            if classes_prof:
                classes_disponibles = [c for c in toutes_classes_ecole if c.libelle and c.libelle.strip().lower() in classes_prof]
            else:
                classes_disponibles = []

            if not classes_disponibles:
                st.warning("⚠️ Aucune classe ne vous est actuellement attribuée. Veuillez contacter l'administration.")
                return

        noms_classes = sorted(list(set(c.libelle for c in classes_disponibles if c.libelle)))

        st.markdown(f"""
            <div class="teacher-card">
                <div style="font-size: 3.5rem; margin-right: 25px;">👨‍🏫</div>
                <div>
                    <h2>Bienvenue, Prof. {username.capitalize()}</h2>
                    <p>Établissement : <b>{school_name}</b> &nbsp;|&nbsp; Accès : <b>Collège / Lycée (Multi-cycles)</b></p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="context-box">', unsafe_allow_html=True)
        st.markdown("#### 🎯 Paramètres de la séance (Basculement dynamique Collège / Lycée)")
        col1, col2 = st.columns(2)
        with col1:
            classe_enseignant = st.selectbox("Vos classes assignées (Collège & Lycée)", noms_classes, key="ens_classe_select")

        classe_obj = next((c for c in classes_disponibles if c.libelle == classe_enseignant), None)
        noms_matieres = get_matieres_classe_strict(classe_obj, ecole_active_id, db, enseignant_obj)

        with col2:
            matiere_enseignant = st.selectbox("Vos matières dispensées", noms_matieres if noms_matieres else ["Aucune matière trouvée"], key="ens_matiere_select")
        st.markdown('</div>', unsafe_allow_html=True)

        matieres_brutes_db = db.query(Matiere).filter(Matiere.school_id == ecole_active_id).all()
        matiere_obj = next(
            (m for m in matieres_brutes_db if (m.libelle if hasattr(m, 'libelle') and m.libelle else getattr(m, 'nom', '')).title() == matiere_enseignant),
            None,
        )

        eleves = []
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id, Eleve.school_id == ecole_active_id)
            if hasattr(Eleve, "deleted_at"):
                eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))
            eleves = eleves_query.order_by(Eleve.nom).all()

        tab_cahier, tab_notes, tab_appel, tab_charge = st.tabs([
            "📖 Cahier de Texte",
            "📝 Saisie des Notes",
            "📋 Feuille d'Appel",
            "📊 Horaires & Reste à faire",
        ])

        with tab_cahier:
            st.markdown(f"<h4 class='tab-title'>📖 Remplir le Cahier de Texte — {classe_enseignant} ({matiere_enseignant})</h4>", unsafe_allow_html=True)
            with st.form("form_ens_cahier_texte_avance"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    date_seance = st.date_input("Date de la séance", value=datetime.now().date(), key="ens_date_cours")
                with col_c2:
                    duree_seance = st.selectbox("Durée de la séance", ["1 heure", "2 heures", "3 heures", "4 heures"], key="ens_duree_seance")

                titre_seance = st.text_input("Titre du cours ou du chapitre *", placeholder="Ex: Chapitre 3 - Les équations du premier degré", key="ens_titre_cours")
                contenu_seance = st.text_area("Contenu réalisé / Résumé de la leçon *", placeholder="Détaillez les notions et le contenu dispensé...", key="ens_contenu_cours")
                
                with st.expander("➕ Ajouter des remarques ou exercices (Optionnel)"):
                    difficultees = st.text_area("Difficultés rencontrées / Remarques", placeholder="Observations pédagogiques particulières...", key="ens_difficultees")
                    mesures_correctives = st.text_area("Mesures correctives / Travail à faire", placeholder="Exercices assignés pour la prochaine séance...", key="ens_mesures")

                submitted_cahier = st.form_submit_button("📤 Enregistrer & Transmettre à l'Inspection", type="primary")
                
                if submitted_cahier:
                    if not titre_seance.strip() or not contenu_seance.strip():
                        st.error("⚠️ Veuillez renseigner le titre et le contenu détaillé du cours.")
                    elif not classe_obj or not matiere_obj:
                        st.error("⚠️ Classe ou matière invalide.")
                    else:
                        nouvelle_entree = CahierTexte(
                            school_id=ecole_active_id,
                            cycle=getattr(classe_obj, 'cycle', 'Collège / Lycée'),
                            classe_id=classe_obj.id,
                            matiere_id=matiere_obj.id,
                            user_id=st.session_state.get("user_id"),
                            date_cours=datetime.combine(date_seance, datetime.min.time()),
                            duree_seance=duree_seance,
                            titre=titre_seance.strip(),
                            contenu=contenu_seance.strip(),
                            difficultees=difficultees.strip() if difficultees else None,
                            mesures_correctives=mesures_correctives.strip() if mesures_correctives else None,
                            est_substitue=0,
                            auteur_saisie=username,
                            statut_validation="Validé",
                        )
                        db.add(nouvelle_entree)
                        db.commit()
                        st.success("✅ Entrée du cahier de texte enregistrée et transmise au registre de l'établissement avec succès !")

        with tab_notes:
            st.markdown(f"<h4 class='tab-title'>📝 Grille d'Évaluation — {classe_enseignant} ({matiere_enseignant})</h4>", unsafe_allow_html=True)
            if not eleves:
                st.markdown(f"""
                    <div class="empty-state">
                        <div style="font-size: 3rem; margin-bottom: 10px;">👥</div>
                        <h4>Aucun élève trouvé</h4>
                        <p>Il n'y a actuellement aucun élève inscrit dans la classe de {classe_enseignant}.</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    type_evaluation = st.selectbox("Type d'évaluation", ["Interro 1", "Interro 2", "Devoir 1", "Devoir 2", "Compo"], key="ens_type_eval")
                with col_n2:
                    semestre = st.selectbox("Période Académique", ["Semestre 1", "Semestre 2", "Trimestre 1", "Trimestre 2", "Trimestre 3"], key="ens_semestre_notes")

                with st.form("form_ens_notes_saisie"):
                    saisie_temp = {}
                    for e in eleves:
                        saisie_temp[e.id] = st.number_input(
                            f"👤 {e.nom} {e.prenom} (Matricule: {getattr(e, 'matricule', 'N/A')}) — Note sur 20",
                            min_value=0.0,
                            max_value=20.0,
                            value=0.0,
                            step=0.25,
                            key=f"ens_note_{e.id}",
                        )

                    submitted_notes = st.form_submit_button("💾 Synchroniser les notes avec l'administration", type="primary")
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

        with tab_appel:
            st.markdown(f"<h4 class='tab-title'>📋 Contrôle de Présence & Discipline — {classe_enseignant}</h4>", unsafe_allow_html=True)
            if not eleves:
                st.markdown(f"""
                    <div class="empty-state">
                        <div style="font-size: 3rem; margin-bottom: 10px;">📋</div>
                        <h4>Liste d'appel indisponible</h4>
                        <p>Veuillez vérifier l'inscription des élèves dans cette classe.</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                date_appel = st.date_input("Date de l'appel", value=datetime.now().date(), key="ens_date_appel")
                
                data_appel = []
                for e in eleves:
                    data_appel.append({
                        "eleve_id": e.id,
                        "Matricule": getattr(e, "matricule", "N/A"),
                        "Nom & Prénom": f"{e.nom} {e.prenom}",
                        "Statut": "Présent",
                        "Précisions / Motif": "—",
                    })
                df_appel = pd.DataFrame(data_appel)
                
                edited_appel = st.data_editor(
                    df_appel,
                    use_container_width=True,
                    column_config={
                        "Statut": st.column_config.SelectboxColumn(
                            "Statut",
                            help="Sélectionner le statut de l'élève",
                            options=["Présent", "Absent", "Retard", "Puni", "Exclu"],
                            required=True,
                        ),
                        "Précisions / Motif": st.column_config.TextColumn(
                            "Précisions / Motif",
                            help="Durée du retard, motif d'absence, etc.",
                        ),
                    },
                    key=f"ens_appel_editor_{classe_enseignant}"
                )

                if st.button("📤 Valider et transmettre l'appel à la vie scolaire", type="primary"):
                    for index, row in edited_appel.iterrows():
                        statut_choisi = str(row["Statut"])
                        precision_str = str(row["Précisions / Motif"])
                        
                        statut_final = statut_choisi
                        if precision_str and precision_str != "—":
                            statut_final = f"{statut_choisi} ({precision_str})"

                        presence_obj = Presence(
                            school_id=ecole_active_id,
                            eleve_id=int(row["eleve_id"]),
                            date=date_appel,
                            statut=statut_final,
                            motif=precision_str if precision_str != "—" else None,
                        )
                        db.add(presence_obj)
                    db.commit()
                    st.success("✅ Feuille d'appel et de discipline validée et transmise avec succès !")

        with tab_charge:
            st.markdown(f"<h4 class='tab-title'>📊 Progression et Heures — {matiere_enseignant} ({classe_enseignant})</h4>", unsafe_allow_html=True)

            if classe_obj and matiere_obj:
                programmes_ecole = db.query(Programme).filter(Programme.school_id == ecole_active_id).all()
                mat_lib = matiere_obj.libelle if hasattr(matiere_obj, "libelle") and matiere_obj.libelle else getattr(matiere_obj, "nom", "Matière")
                mat_norm = normaliser_chaine(mat_lib)

                volume_prevu = 0.0
                for attr_v in ["volume_horaire", "volume", "heures", "masse_horaire", "duree", "volume_hebdo"]:
                    val = getattr(matiere_obj, attr_v, None)
                    if val is not None:
                        try:
                            v_f = float(val)
                            if v_f > 0:
                                volume_prevu = v_f
                                break
                        except Exception:
                            pass
                
                if volume_prevu == 0.0:
                    for p in programmes_ecole:
                        p_nom = normaliser_chaine(getattr(p, 'nom_matiere', getattr(p, 'matiere', '')))
                        if p_nom == mat_norm and p.volume_horaire:
                            try:
                                volume_prevu = float(p.volume_horaire)
                                break
                            except Exception:
                                pass

                volume_total_prevu = volume_prevu
                tances_entrees = db.query(CahierTexte).filter(CahierTexte.school_id == ecole_active_id, CahierTexte.classe_id == classe_obj.id).all()
                
                # CORRECTION ROBUSTE : Association élargie par ID, correspondance normalisée ou présence du nom de la matière
                seances_mat = [
                    e for e in tances_entrees 
                    if (getattr(e, 'matiere_id', None) == matiere_obj.id) or 
                       (normaliser_chaine(getattr(e, 'matiere', getattr(e, 'discipline', ''))) == mat_norm) or
                       (mat_norm in normaliser_chaine(getattr(e, 'matiere', getattr(e, 'discipline', '')))) or
                       (mat_norm in normaliser_chaine(getattr(e, 'titre', ''))) or
                       (mat_norm in normaliser_chaine(getattr(e, 'contenu', '')))
                ]

                volume_dispense = 0.0
                for seance in seances_mat:
                    duree_val = float(getattr(seance, 'duree', 0.0) or 0.0)
                    if duree_val > 0:
                        volume_dispense += duree_val
                    else:
                        d_str = str(getattr(seance, "duree_seance", "1 heure"))
                        try:
                            chiffre = float("".join(filter(str.isdigit, d_str)) or 1)
                            volume_dispense += chiffre
                        except Exception:
                            volume_dispense += 1.0

                reste_a_recouvrer = max(0.0, volume_total_prevu - volume_dispense)
                progression_pct = min(100, int((volume_dispense / volume_total_prevu) * 100) if volume_total_prevu > 0 else 0)

                col_h1, col_h2, col_h3 = st.columns(3)
                with col_h1:
                    st.metric("Volume Horaire Dispensé", f"{volume_dispense:g}h")
                with col_h2:
                    st.metric("Volume Total Annuel Prévu", f"{volume_total_prevu:g}h")
                with col_h3:
                    st.metric("Reste à Faire", f"{reste_a_recouvrer:g}h")

                st.progress(max(0.0, min(1.0, progression_pct / 100.0)), text=f"Progression globale du programme : {progression_pct}%")
            else:
                st.info("Veuillez sélectionner une classe et une matière valides.")

    finally:
        db.close()


afficher_enseignants = afficher_espace_enseignants
afficher_espace_enseignant = afficher_espace_enseignants