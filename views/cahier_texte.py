from datetime import datetime
import unicodedata
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import Affectation, ActivityLog, CahierTexte, Classe, Enseignant, Matiere, School, User

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

def get_matieres_dynamiques_cahier(selected_classes_labels, classes_cycle, ecole_active_id, cycle_en_cours, db):
    m_brutes = []
    if selected_classes_labels:
        sel_ids = [c.id for c in classes_cycle if c.libelle in selected_classes_labels]
        if sel_ids:
            try:
                mat_q = db.query(Matiere).filter(
                    Matiere.school_id == ecole_active_id, 
                    Matiere.classe_id.in_(sel_ids)
                )
                if hasattr(Matiere, "deleted_at"):
                    mat_q = mat_q.filter(Matiere.deleted_at.is_(None))
                m_brutes = mat_q.all()
            except Exception:
                m_brutes = []

    if not m_brutes and cycle_en_cours:
        try:
            mat_q_cycle = db.query(Matiere).filter(Matiere.school_id == ecole_active_id)
            if hasattr(Matiere, "cycle"):
                mat_q_cycle = mat_q_cycle.filter(Matiere.cycle.ilike(f"%{cycle_en_cours}%"))
            if hasattr(Matiere, "deleted_at"):
                mat_q_cycle = mat_q_cycle.filter(Matiere.deleted_at.is_(None))
            m_brutes = mat_q_cycle.all()
        except Exception:
            m_brutes = []

    if not m_brutes:
        try:
            mat_q_all = db.query(Matiere).filter(Matiere.school_id == ecole_active_id)
            if hasattr(Matiere, "deleted_at"):
                mat_q_all = mat_q_all.filter(Matiere.deleted_at.is_(None))
            m_brutes = mat_q_all.all()
        except Exception:
            m_brutes = []

    m_dict = {}
    cycle_actuel_lower = str(cycle_en_cours).lower()
    for m in m_brutes:
        n_brut = m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "Matière")
        n_key = normaliser_chaine(n_brut)
        if "collège" in cycle_actuel_lower or "college" in cycle_actuel_lower:
            if "philosophie" in n_key or "philo" in n_key:
                continue
        if n_key and n_key not in m_dict:
            libelle_propre = n_brut.strip().title()
            if "economie familiale" in n_key:
                libelle_propre = "Économie Familiale Et Sociale"
            m_dict[n_key] = libelle_propre
    return sorted(list(m_dict.values()))

def afficher_cahier_texte():
    st.markdown("## 📖 Cahier de Texte Numérique")
    st.markdown("Suivi centralisé des cours dispensés, des contenus pédagogiques, des durées et des devoirs.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    role_utilisateur = str(st.session_state.get("role", "")).lower()
    username = st.session_state.get("username", "admin")
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    est_admin = is_super_admin or "admin" in role_utilisateur or "directeur" in role_utilisateur

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        user_obj = db.query(User).filter(User.username == username).first()
        user_id_val = user_obj.id if user_obj else None

        enseignants_query = db.query(Enseignant).filter(Enseignant.school_id == target_school_id)
        if hasattr(Enseignant, "deleted_at"):
            enseignants_query = enseignants_query.filter(Enseignant.deleted_at.is_(None))
        tous_enseignants = enseignants_query.all()
        dict_ens_options = {f"{e.nom} {e.prenom}".strip(): e.id for e in tous_enseignants}
        dict_ens_par_id = {e.id: f"{e.nom} {e.prenom}".strip() for e in tous_enseignants}

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)

        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        classes_cycle = classes_query.all()

        if not classes_cycle:
            st.warning(f"⚠️ Veuillez configurer des classes pour le cycle **{cycle_en_cours}**.")
            return

        noms_classes = [c.libelle for c in classes_cycle]

        tab1, tab2 = st.tabs([
            "📖 Consulter le Cahier de Texte",
            "✍️ Saisir un Cours / Devoir",
        ])

        with tab1:
            st.markdown(f"<h4 class='tab-title'>Entrées du Cahier de Texte — {cycle_en_cours}</h4>", unsafe_allow_html=True)
            classe_consult = st.selectbox("Sélectionner la classe à consulter", noms_classes, key="consult_cahier_classe")

            classe_obj = next((c for c in classes_cycle if c.libelle == classe_consult), None)
            if classe_obj:
                entrees_db = (
                    db.query(CahierTexte)
                    .filter(
                        CahierTexte.school_id == target_school_id,
                        CahierTexte.classe_id == classe_obj.id,
                    )
                    .order_by(CahierTexte.date_cours.desc(), CahierTexte.id.desc())
                    .all()
                )

                if not entrees_db:
                    st.info(f"Aucune entrée enregistrée pour la classe {classe_consult}.")
                else:
                    for e in entrees_db:
                        matiere_obj = db.query(Matiere).filter(Matiere.id == e.matiere_id).first()
                        nom_matiere = (matiere_obj.libelle if hasattr(matiere_obj, "libelle") and matiere_obj.libelle else getattr(matiere_obj, "nom", "Matière")) if matiere_obj else "Matière"
                        
                        nom_enseignant_affiche = e.auteur_saisie or "Administration"
                        if hasattr(e, "enseignant_id") and e.enseignant_id:
                            ens_lie = db.query(Enseignant).filter(Enseignant.id == e.enseignant_id).first()
                            if ens_lie:
                                nom_enseignant_affiche = f"{getattr(ens_lie, 'nom', '')} {getattr(ens_lie, 'prenom', '')}".strip()

                        date_str = e.date_cours.strftime("%d/%m/%Y %H:%M") if isinstance(e.date_cours, datetime) else (str(e.date_cours) if e.date_cours else "N/D")
                        duree_val = getattr(e, "duree_seance", "1 heure")
                        titre = e.titre or 'Séance sans titre'

                        with st.expander(f"{date_str} — {nom_matiere.title()} ({duree_val}) | {titre}"):
                            st.write(f"**Enseignant(e) :** {nom_enseignant_affiche}")
                            st.write(f"**Contenu :**")
                            st.write(e.contenu)

                            if est_admin:
                                st.markdown("---")
                                st.markdown("##### ⚙️ Administration : Gérer la séance")
                                
                                list_noms_ens = list(dict_ens_options.keys())
                                current_ens_index = 0
                                if hasattr(e, "enseignant_id") and e.enseignant_id:
                                    for idx, nom_opt in enumerate(list_noms_ens):
                                        if dict_ens_options.get(nom_opt) == e.enseignant_id:
                                            current_ens_index = idx
                                            break

                                col_reassign1, col_reassign2 = st.columns([2, 1])
                                with col_reassign1:
                                    nouveau_prof_nom = st.selectbox(
                                        "Réassigner l'enseignant",
                                        options=list_noms_ens,
                                        index=current_ens_index,
                                        key=f"reassign_ens_{e.id}"
                                    )
                                with col_reassign2:
                                    st.write("")
                                    st.write("")
                                    if st.button("👤 Changer prof", key=f"btn_reassign_prof_{e.id}"):
                                        try:
                                            e.enseignant_id = dict_ens_options.get(nouveau_prof_nom)
                                            db.commit()
                                            st.success("✅ Enseignant réassigné avec succès !")
                                            st.rerun()
                                        except Exception as err:
                                            db.rollback()
                                            st.error(f"Erreur : {err}")

                                st.markdown("---")
                                current_date_val = e.date_cours.date() if isinstance(e.date_cours, datetime) else datetime.now().date()
                                current_time_val = e.date_cours.time() if isinstance(e.date_cours, datetime) else datetime.now().time()
                                
                                duree_actuelle_str = str(getattr(e, "duree_seance", "1 heure"))
                                default_duree_index = 0
                                try:
                                    val_num = float(''.join([c for c in duree_actuelle_str if c.isdigit() or c == '.']))
                                    if val_num in [1.0, 2.0, 3.0, 4.0]:
                                        default_duree_index = [1.0, 2.0, 3.0, 4.0].index(val_num)
                                except Exception:
                                    default_duree_index = 0

                                col_m1, col_m2, col_m3 = st.columns(3)
                                with col_m1:
                                    nouvelle_date = st.date_input("Date", value=current_date_val, key=f"edit_date_{e.id}")
                                with col_m2:
                                    nouvelle_heure = st.time_input("Heure", value=current_time_val, key=f"edit_time_{e.id}")
                                with col_m3:
                                    nouvelle_duree = st.selectbox(
                                        "Durée", 
                                        options=[1.0, 2.0, 3.0, 4.0], 
                                        index=default_duree_index,
                                        format_func=lambda x: f"{int(x)} heure{'s' if x > 1 else ''}", 
                                        key=f"edit_duree_{e.id}"
                                    )

                                col_btn_mod, col_btn_supp = st.columns(2)
                                with col_btn_mod:
                                    if st.button("💾 Mettre à jour", key=f"btn_update_seance_{e.id}"):
                                        try:
                                            e.date_cours = datetime.combine(nouvelle_date, nouvelle_heure)
                                            e.duree_seance = f"{int(nouvelle_duree)} heure{'s' if nouvelle_duree > 1 else ''}"
                                            db.commit()
                                            st.success("✅ Séance mise à jour avec succès !")
                                            st.rerun()
                                        except Exception as err:
                                            db.rollback()
                                            st.error(f"Erreur lors de la mise à jour : {err}")

                                with col_btn_supp:
                                    if st.button("🗑️ Supprimer la séance", key=f"btn_delete_seance_{e.id}", type="secondary"):
                                        st.session_state[f"confirm_del_seance_{e.id}"] = True

                                if st.session_state.get(f"confirm_del_seance_{e.id}", False):
                                    st.warning("⚠️ Voulez-vous vraiment supprimer définitivement cette entrée du cahier de texte ?")
                                    col_c1, col_c2 = st.columns(2)
                                    with col_c1:
                                        if st.button("Oui, supprimer", key=f"yes_del_seance_{e.id}", type="primary"):
                                            try:
                                                db.delete(e)
                                                db.commit()
                                                st.success("✅ Séance supprimée avec succès !")
                                                st.session_state[f"confirm_del_seance_{e.id}"] = False
                                                st.rerun()
                                            except Exception as err:
                                                db.rollback()
                                                st.error(f"Erreur lors de la suppression : {err}")
                                    with col_c2:
                                        if st.button("Annuler", key=f"cancel_del_seance_{e.id}"):
                                            st.session_state[f"confirm_del_seance_{e.id}"] = False
                                            st.rerun()

        with tab2:
            st.markdown("#### Saisie de Cours")
            col1, col2 = st.columns(2)
            with col1:
                classe_choisie = st.selectbox("Classe", noms_classes, key="form_cahier_classe")
                classe_obj_s = next((c for c in classes_cycle if c.libelle == classe_choisie), None)

                noms_matieres = get_matieres_dynamiques_cahier([classe_choisie], classes_cycle, target_school_id, cycle_en_cours, db)
                matiere_choisie = st.selectbox("Matière", noms_matieres if noms_matieres else ["Aucune matière"], key="form_cahier_matiere")
            with col2:
                date_cours = st.date_input("Date du cours", value=datetime.now().date(), key="form_cahier_date")
                duree_cours = st.selectbox("Durée de la séance", options=[1.0, 2.0, 3.0, 4.0], format_func=lambda x: f"{int(x)} heure{'s' if x > 1 else ''}", key="form_cahier_duree")

            # --- DÉTECTION AUTOMATIQUE DE L'ENSEIGNANT ---
            enseignant_trouve_id = None
            enseignant_nom_affiche = ""

            if classe_obj_s and matiere_choisie:
                affectations_q = db.query(Affectation).filter(
                    Affectation.classe_id == classe_obj_s.id,
                    Affectation.school_id == target_school_id
                ).all()
                
                for aff in affectations_q:
                    mat_obj = db.query(Matiere).filter(Matiere.id == aff.matiere_id).first() if hasattr(aff, "matiere_id") and aff.matiere_id else None
                    nom_mat_aff = (mat_obj.libelle if mat_obj and hasattr(mat_obj, "libelle") else getattr(mat_obj, "nom", "")) if mat_obj else str(getattr(aff, "matiere", ""))
                    
                    if normaliser_chaine(nom_mat_aff) == normaliser_chaine(matiere_choisie):
                        enseignant_trouve_id = getattr(aff, "enseignant_id", None)
                        break
                
                if not enseignant_trouve_id:
                    for ens in tous_enseignants:
                        mat_attr = str(getattr(ens, "matieres_attribuees", "") or getattr(ens, "matieres", "")).lower()
                        cls_attr = str(getattr(ens, "classes_attribuees", "") or getattr(ens, "classes", "")).lower()
                        if classe_obj_s.libelle.lower() in cls_attr and normaliser_chaine(matiere_choisie) in normaliser_chaine(mat_attr):
                            enseignant_trouve_id = ens.id
                            break

            if enseignant_trouve_id and enseignant_trouve_id in dict_ens_par_id:
                enseignant_nom_affiche = dict_ens_par_id[enseignant_trouve_id]
            elif tous_enseignants:
                enseignant_nom_affiche = f"{tous_enseignants[0].nom} {tous_enseignants[0].prenom}".strip()
                enseignant_trouve_id = tous_enseignants[0].id

            if enseignant_nom_affiche:
                st.info(f"💡 Enseignant affecté sélectionné automatiquement : **{enseignant_nom_affiche}**")

            liste_noms_ens = list(dict_ens_options.keys())
            defaut_idx = 0
            if enseignant_nom_affiche in liste_noms_ens:
                defaut_idx = liste_noms_ens.index(enseignant_nom_affiche)

            cle_selectbox_ens = f"form_cahier_enseignant_libre_{classe_choisie}_{matiere_choisie}"

            enseignant_nom_selectionne = st.selectbox(
                "Enseignant dispensant le cours (Modifiable si remplacement) *",
                options=liste_noms_ens if liste_noms_ens else [enseignant_nom_affiche],
                index=defaut_idx,
                key=cle_selectbox_ens,
                help="Sélectionnez librement l'enseignant de votre choix pour ce cours."
            )
            enseignant_id_final = dict_ens_options.get(enseignant_nom_selectionne, enseignant_trouve_id)

            titre_cours = st.text_input("Titre du cours *", key="form_cahier_titre")
            contenu = st.text_area("Contenu détaillé de la séance *", key="form_cahier_contenu")

            if st.button("💾 Enregistrer l'entrée dans la base", type="primary", key="form_cahier_submit"):
                if not titre_cours.strip() or not contenu.strip():
                    st.error("⚠️ Veuillez remplir le titre et le contenu détaillé.")
                elif not enseignant_id_final:
                    st.error("⚠️ Veuillez sélectionner l'enseignant.")
                else:
                    cls_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
                    mat_brutes_all = db.query(Matiere).filter(Matiere.school_id == target_school_id).all()
                    mat_obj = next((m for m in mat_brutes_all if (m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "")).strip().title() == matiere_choisie), None)

                    nouvelle_entree = CahierTexte(
                        school_id=target_school_id,
                        cycle=cycle_en_cours,
                        classe_id=cls_obj.id if cls_obj else None,
                        matiere_id=mat_obj.id if mat_obj else None,
                        enseignant_id=enseignant_id_final,
                        user_id=user_id_val,
                        date_cours=datetime.combine(date_cours, datetime.now().time()),
                        duree_seance=f"{int(duree_cours)} heure{'s' if duree_cours > 1 else ''}",
                        titre=titre_cours.strip(),
                        contenu=contenu.strip(),
                        auteur_saisie=username,
                        statut_validation="Validé",
                    )
                    db.add(nouvelle_entree)
                    db.commit()
                    st.success("✅ Entrée enregistrée avec succès !")
                    st.rerun()

    except Exception as e:
        st.error(f"Une erreur est survenue lors de l'exécution : {e}")
    finally:
        db.close()

afficher_cahier_de_texte = afficher_cahier_texte