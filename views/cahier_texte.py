from datetime import datetime
import unicodedata
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import ActivityLog, CahierTexte, Classe, Enseignant, Matiere, School, User

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
    st.markdown("""
        <style>
        .cahier-card {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            border-left: 5px solid #4da6ff;
        }
        .cahier-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .cahier-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #e2e8f0; }
        .filter-box {
            background-color: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
        }
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            background-color: rgba(255,255,255,0.03);
            border-radius: 12px;
            color: #a0aec0;
            border: 1px dashed rgba(255,255,255,0.2);
            margin-top: 15px;
            margin-bottom: 20px;
        }
        .empty-state h4 { color: #e2e8f0; margin-top: 10px; margin-bottom: 5px; }
        .tab-title { color: #4da6ff; font-weight: 600; margin-bottom: 15px; }
        .entry-badge {
            display: inline-block;
            padding: 4px 8px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            font-size: 0.85rem;
            margin-right: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .delete-section {
            background-color: rgba(220, 53, 69, 0.05);
            border: 1px solid rgba(220, 53, 69, 0.2);
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 📖 Cahier de Texte Numérique")
    st.markdown("Suivi centralisé des cours dispensés, des contenus pédagogiques, des durées et des devoirs.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    role_utilisateur = str(st.session_state.get("role", "")).lower()
    username = st.session_state.get("username", "admin")
    school_name = st.session_state.get("school_name", "Établissement")
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

        st.markdown(f"""
            <div class="cahier-card">
                <div style="font-size: 3.5rem; margin-right: 25px;">📓</div>
                <div>
                    <h2>Registre des Séances</h2>
                    <p>Établissement : <b>{school_name}</b> &nbsp;|&nbsp; Cycle : <b>{cycle_en_cours}</b></p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        user_obj = db.query(User).filter(User.username == username).first()
        user_id_val = user_obj.id if user_obj else None

        enseignants_query = db.query(Enseignant).filter(Enseignant.school_id == target_school_id)
        if hasattr(Enseignant, "deleted_at"):
            enseignants_query = enseignants_query.filter(Enseignant.deleted_at.is_(None))
        tous_enseignants = enseignants_query.all()
        dict_ens_options = {f"{e.nom} {e.prenom}".strip(): e.id for e in tous_enseignants}

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
            st.markdown('<div class="filter-box">', unsafe_allow_html=True)
            classe_consult = st.selectbox("Sélectionner la classe à consulter", noms_classes, key="consult_cahier_classe")
            st.markdown('</div>', unsafe_allow_html=True)

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
                    st.markdown(f"""
                        <div class="empty-state">
                            <div style="font-size: 3rem; margin-bottom: 10px;">📓</div>
                            <h4>Aucune entrée enregistrée</h4>
                            <p>Le cahier de texte de la classe <b>{classe_consult}</b> est actuellement vierge dans ce cycle.</p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    for e in entrees_db:
                        matiere_obj = db.query(Matiere).filter(Matiere.id == e.matiere_id).first()
                        nom_matiere = (matiere_obj.libelle if hasattr(matiere_obj, "libelle") and matiere_obj.libelle else getattr(matiere_obj, "nom", "Matière non spécifiée")) if matiere_obj else "Matière non spécifiée"
                        
                        nom_enseignant_affiche = e.auteur_saisie or "Administration"
                        if hasattr(e, "enseignant_id") and e.enseignant_id:
                            ens_lie = db.query(Enseignant).filter(Enseignant.id == e.enseignant_id).first()
                            if ens_lie:
                                nom_enseignant_affiche = f"{getattr(ens_lie, 'nom', '')} {getattr(ens_lie, 'prenom', '')}".strip()

                        date_str = e.date_cours.strftime("%d/%m/%Y") if e.date_cours else "N/D"
                        duree_val = getattr(e, "duree_seance", "1 heure")
                        titre = e.titre or 'Séance sans titre'
                        visa_status = getattr(e, 'visa_inspecteur', None)
                        icon_visa = "✅" if visa_status else "⏳"

                        with st.expander(f"{icon_visa} {date_str} — {nom_matiere.title()} ({duree_val}) | {titre}"):
                            st.markdown(f"<span class='entry-badge'>👨‍🏫 Enseignant(e) : {nom_enseignant_affiche}</span>", unsafe_allow_html=True)
                            st.markdown(f"<span class='entry-badge'>🔖 ID : {e.id}</span>", unsafe_allow_html=True)
                            if visa_status:
                                st.markdown(f"<span class='entry-badge' style='background-color: rgba(72,187,120,0.15); border-color: #48bb78; color: #48bb78;'>🛡️ {visa_status}</span>", unsafe_allow_html=True)
                            st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                            st.markdown("**📝 Contenu de la séance :**")
                            st.write(e.contenu)
                            if e.difficultees:
                                st.markdown("**⚠️ Difficultés / Remarques :**")
                                st.write(e.difficultees)

                    # --- SECTION GESTION, RECTIFICATION & SUPPRESSION ---
                    st.markdown(f'<div class="delete-section">', unsafe_allow_html=True)
                    st.markdown("#### ✏️ Rectification de la durée & Suppression de séances")
                    st.markdown("Permet de corriger la durée d'une séance suite à une réclamation d'un enseignant ou de supprimer un doublon (ex: ID 194/195).")
                    
                    options_suppr = {}
                    for e in entrees_db:
                        d_str = e.date_cours.strftime('%d/%m/%Y') if e.date_cours else ''
                        t_str = e.titre or 'Cours'
                        duree_actuelle = getattr(e, "duree_seance", "1 heure")
                        libelle_opt = f"ID {e.id} — {d_str} — {t_str} ({duree_actuelle})"
                        options_suppr[libelle_opt] = e.id

                    entree_selectionnee_label = st.selectbox(
                        "Sélectionner la séance concernée",
                        list(options_suppr.keys()),
                        key="select_gestion_cahier",
                    )
                    
                    id_selectionne = options_suppr[entree_selectionnee_label]
                    entree_obj = db.query(CahierTexte).filter(CahierTexte.id == id_selectionne).first()

                    if entree_obj:
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            nouvelle_duree_num = st.selectbox(
                                "Modifier la durée de la séance",
                                options=[1.0, 2.0, 3.0, 4.0],
                                format_func=lambda x: f"{int(x)} heure{'s' if x > 1 else ''}",
                                key=f"mod_duree_{id_selectionne}"
                            )
                            if st.button("💾 Mettre à jour la durée", type="primary"):
                                duree_str_new = f"{int(nouvelle_duree_num)} heure{'s' if nouvelle_duree_num > 1 else ''}"
                                ancienne_duree = getattr(entree_obj, "duree_seance", "N/D")
                                entree_obj.duree_seance = duree_str_new
                                
                                nouveau_log = ActivityLog(
                                    school_id=target_school_id,
                                    timestamp=datetime.now(),
                                    username=username,
                                    action=f"Modification durée séance ID {id_selectionne} ({ancienne_duree} -> {duree_str_new})",
                                    module="Cahier de Texte",
                                    statut="Succès",
                                )
                                db.add(nouveau_log)
                                db.commit()
                                st.success(f"✅ Durée mise à jour avec succès à **{duree_str_new}** !")
                                st.rerun()

                        with col_m2:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("🗑️ Supprimer cette séance (Doublon)", type="secondary"):
                                db.delete(entree_obj)
                                nouveau_log = ActivityLog(
                                    school_id=target_school_id,
                                    timestamp=datetime.now(),
                                    username=username,
                                    action=f"Suppression entrée Cahier de Texte ID {id_selectionne} ({classe_consult})",
                                    module="Cahier de Texte",
                                    statut="Succès",
                                )
                                db.add(nouveau_log)
                                db.commit()
                                st.success("✅ Entrée supprimée avec succès !")
                                st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            if role_utilisateur == "enseignant":
                st.markdown(f"<h4 class='tab-title'>Espace Enseignant — Saisie de votre cours ({username})</h4>", unsafe_allow_html=True)
            else:
                st.markdown(f"<h4 class='tab-title'>Saisie / Substitution Censeur & Administration</h4>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                classe_choisie = st.selectbox("Classe", noms_classes, key="form_cahier_classe")
                noms_matieres = get_matieres_dynamiques_cahier([classe_choisie], classes_cycle, target_school_id, cycle_en_cours, db)
                matiere_choisie = st.selectbox("Matière", noms_matieres if noms_matieres else ["Aucune matière"], key="form_cahier_matiere")
            with col2:
                date_cours = st.date_input("Date du cours", value=datetime.now().date(), key="form_cahier_date")
                duree_cours = st.selectbox(
                    "Durée de la séance",
                    options=[1.0, 2.0, 3.0, 4.0],
                    format_func=lambda x: f"{int(x)} heure{'s' if x > 1 else ''}",
                    key="form_cahier_duree"
                )

            enseignant_suggere_nom = "Aucun titulaire détecté automatiquement"
            enseignant_id_final = None
            
            if dict_ens_options and classe_choisie and matiere_choisie:
                cls_obj_cherche = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
                matiere_norm = normaliser_chaine(matiere_choisie)
                if cls_obj_cherche:
                    for e in tous_enseignants:
                        mat_attr = str(getattr(e, "matieres_attribuees", "") or getattr(e, "matieres", "")).lower()
                        cls_attr = str(getattr(e, "classes_attribuees", "") or getattr(e, "classes", "")).lower()
                        if (matiere_norm in normaliser_chaine(mat_attr) or matiere_choisie.lower() in mat_attr) and \
                           (cls_obj_cherche.libelle.lower() in cls_attr):
                            enseignant_suggere_nom = f"{e.nom} {e.prenom}".strip()
                            enseignant_id_final = e.id
                            break

            st.info(f"💡 **Titulaire suggéré :** {enseignant_suggere_nom}")

            if "last_classe_matiere_cahier" not in st.session_state:
                st.session_state["last_classe_matiere_cahier"] = ("", "")

            current_combo = (classe_choisie, matiere_choisie)
            if st.session_state["last_classe_matiere_cahier"] != current_combo:
                st.session_state["last_classe_matiere_cahier"] = current_combo
                if enseignant_suggere_nom in dict_ens_options:
                    st.session_state["form_cahier_enseignant"] = enseignant_suggere_nom

            liste_noms_ens = list(dict_ens_options.keys())
            
            enseignant_nom_selectionne = st.selectbox(
                "Enseignant dispensant le cours (Modifiable si remplacement) *",
                options=liste_noms_ens,
                key="form_cahier_enseignant",
                help="Le système pré-sélectionne instantanément le professeur titulaire de cette matière dans cette classe."
            )
            enseignant_id_final = dict_ens_options.get(enseignant_nom_selectionne)

            titre_cours = st.text_input("Titre / Intitulé du cours ou du devoir *", placeholder="Ex: Chapitre 1 - Les bases", key="form_cahier_titre")
            contenu = st.text_area("Contenu détaillé de la séance / Travail à faire *", placeholder="Déroulement de la leçon...", key="form_cahier_contenu")
            
            with st.expander("➕ Options supplémentaires"):
                difficultees = st.text_area("Difficultés particulières observées (optionnel)", placeholder="Remarques...", key="form_cahier_diff")

            if st.button("💾 Enregistrer l'entrée dans la base", type="primary", key="form_cahier_submit"):
                if not titre_cours.strip() or not contenu.strip():
                    st.error("⚠️ Veuillez remplir le titre et le contenu détaillé de la séance.")
                elif not enseignant_id_final:
                    st.error("⚠️ Veuillez sélectionner l'enseignant dispensant le cours.")
                else:
                    cls_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
                    mat_brutes_all = db.query(Matiere).filter(Matiere.school_id == target_school_id).all()
                    mat_obj = next(
                        (m for m in mat_brutes_all if (m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "")).strip().title() == matiere_choisie), 
                        None
                    )

                    # --- CONTRÔLE ANTI-DOUBLON STRICT (Classe + Matière + Date) ---
                    date_debut_jour = datetime.combine(date_cours, datetime.min.time())
                    date_fin_jour = datetime.combine(date_cours, datetime.max.time())

                    doublon_existant = db.query(CahierTexte).filter(
                        CahierTexte.school_id == target_school_id,
                        CahierTexte.classe_id == (cls_obj.id if cls_obj else None),
                        CahierTexte.matiere_id == (mat_obj.id if mat_obj else None),
                        CahierTexte.date_cours >= date_debut_jour,
                        CahierTexte.date_cours <= date_fin_jour
                    ).first()

                    if doublon_existant:
                        st.error(f"⚠️ **Erreur de saisie :** Un cours pour la classe **{classe_choisie}** en **{matiere_choisie}** a **déjà été enregistré** à la date du **{date_cours.strftime('%d/%m/%Y')}** (ID : {doublon_existant.id}). Impossible de le saisir deux fois.")
                    else:
                        contenu_formate = f"**[{titre_cours.strip()}]**\n{contenu.strip()}"
                        duree_str = f"{int(duree_cours)} heure{'s' if duree_cours > 1 else ''}"

                        nouvelle_entree = CahierTexte(
                            school_id=target_school_id,
                            cycle=cycle_en_cours,
                            classe_id=cls_obj.id if cls_obj else None,
                            matiere_id=mat_obj.id if mat_obj else None,
                            enseignant_id=enseignant_id_final,
                            user_id=user_id_val,
                            date_cours=datetime.combine(date_cours, datetime.now().time()),
                            duree_seance=duree_str,
                            titre=titre_cours.strip(),
                            contenu=contenu_formate,
                            difficultees=difficultees.strip() if difficultees else None,
                            auteur_saisie=username,
                            statut_validation="Validé",
                        )
                        db.add(nouvelle_entree)
                        db.commit()

                        st.success(f"✅ Entrée enregistrée ({duree_str}) pour la classe **{classe_choisie}** en **{matiere_choisie}** !")
                        st.rerun()

    finally:
        db.close()

afficher_cahier_de_texte = afficher_cahier_texte