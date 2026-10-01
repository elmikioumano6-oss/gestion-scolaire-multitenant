from datetime import datetime
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import ActivityLog, CahierTexte, Classe, Matiere, School, User


def afficher_cahier_texte():
    # --- Injection CSS pour un design Premium ---
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
        .tab-title {
            color: #4da6ff;
            font-weight: 600;
            margin-bottom: 15px;
        }
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
    st.markdown(
        "Suivi centralisé des cours dispensés, des contenus pédagogiques, des durées et des devoirs "
        "avec isolation multi-tenant et persistance en base de données."
    )
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

        # --- 1. Carte Registre Officiel ---
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

        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        matieres_query = db.query(Matiere).filter(Matiere.cycle == cycle_en_cours)

        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)
            matieres_query = matieres_query.filter(Matiere.school_id == target_school_id)

        classes_cycle = classes_query.all()
        matieres_cycle = matieres_query.all()

        if not classes_cycle or not matieres_cycle:
            st.warning(
                f"⚠️ Veuillez vous assurer d'avoir enregistré des classes et des "
                f"matières pour le cycle **{cycle_en_cours}**."
            )
            st.info("Utilisez les modules du menu latéral pour les configurer.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        noms_matieres = [
            m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "")
            for m in matieres_cycle
        ]

        tab1, tab2 = st.tabs([
            "📖 Consulter le Cahier de Texte",
            "✍️ Saisir un Cours / Devoir (Enseignant ou Substitution Censeur)",
        ])

        # ==========================================
        # ONGLET 1 : CONSULTATION
        # ==========================================
        with tab1:
            st.markdown(f"<h4 class='tab-title'>Entrées du Cahier de Texte — {cycle_en_cours}</h4>", unsafe_allow_html=True)
            
            st.markdown('<div class="filter-box">', unsafe_allow_html=True)
            classe_consult = st.selectbox(
                "Sélectionner la classe à consulter",
                noms_classes,
                key="consult_cahier_classe",
            )
            st.markdown('</div>', unsafe_allow_html=True)

            classe_obj = next(
                (c for c in classes_cycle if c.libelle == classe_consult), None
            )

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
                    # Affichage sous forme de liste expansible élégante
                    for e in entrees_db:
                        matiere_obj = db.query(Matiere).filter(Matiere.id == e.matiere_id).first()
                        nom_matiere = (matiere_obj.libelle if hasattr(matiere_obj, "libelle") and matiere_obj.libelle else getattr(matiere_obj, "nom", "Matière non spécifiée")) if matiere_obj else "Matière non spécifiée"
                        date_str = e.date_cours.strftime("%d/%m/%Y") if e.date_cours else "N/D"
                        duree_val = getattr(e, "duree_seance", "1 heure")
                        titre = e.titre or 'Séance sans titre'
                        auteur = e.auteur_saisie or "Administration"
                        visa_status = getattr(e, 'visa_inspecteur', None)
                        icon_visa = "✅" if visa_status else "⏳"

                        with st.expander(f"{icon_visa} {date_str} — {nom_matiere.title()} ({duree_val}) | {titre}"):
                            st.markdown(f"<span class='entry-badge'>👨‍🏫 Enseignant(e) : {auteur}</span>", unsafe_allow_html=True)
                            st.markdown(f"<span class='entry-badge'>🔖 ID : {e.id}</span>", unsafe_allow_html=True)
                            if visa_status:
                                st.markdown(f"<span class='entry-badge' style='background-color: rgba(72,187,120,0.15); border-color: #48bb78; color: #48bb78;'>🛡️ {visa_status}</span>", unsafe_allow_html=True)
                            st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                            
                            st.markdown("**📝 Contenu de la séance :**")
                            st.write(e.contenu)
                            
                            if e.difficultees:
                                st.markdown("**⚠️ Difficultés / Remarques :**")
                                st.write(e.difficultees)

                    # Section de suppression stylisée
                    st.markdown(f'<div class="delete-section">', unsafe_allow_html=True)
                    st.markdown("#### 🗑️ Gestion & Suppression d'une entrée")
                    options_suppr = {
                        f"ID {e.id} — {e.date_cours.strftime('%d/%m/%Y') if e.date_cours else ''} — {e.titre or 'Cours'}": e.id
                        for e in entrees_db
                    }
                    entree_a_supprimer_label = st.selectbox(
                        "Sélectionner l'entrée à supprimer",
                        list(options_suppr.keys()),
                        key="select_suppr_cahier",
                    )

                    if st.button("🗑️ Supprimer l'entrée sélectionnée", type="secondary"):
                        id_a_supprimer = options_suppr[entree_a_supprimer_label]
                        entree_obj = db.query(CahierTexte).filter(CahierTexte.id == id_a_supprimer).first()
                        if entree_obj:
                            db.delete(entree_obj)

                            nouveau_log = ActivityLog(
                                school_id=target_school_id,
                                timestamp=datetime.now(),
                                username=username,
                                action=f"Suppression entrée Cahier de Texte ID {id_a_supprimer} ({classe_consult})",
                                module="Cahier de Texte",
                                statut="Succès",
                            )
                            db.add(nouveau_log)
                            db.commit()
                            st.success("✅ Entrée supprimée avec succès ! Les statistiques ont été mises à jour.")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        # ==========================================
        # ONGLET 2 : SAISIE
        # ==========================================
        with tab2:
            if role_utilisateur == "enseignant":
                st.markdown(f"<h4 class='tab-title'>Espace Enseignant — Saisie de votre cours ({username})</h4>", unsafe_allow_html=True)
            else:
                st.markdown(f"<h4 class='tab-title'>Saisie / Substitution Censeur & Administration</h4>", unsafe_allow_html=True)
                st.info("💡 En tant que censeur ou directeur, vous pouvez remplir ce cahier si l'enseignant vacataire n'a pas pu le faire.")

            with st.form("form_add_cahier_db"):
                col1, col2 = st.columns(2)
                with col1:
                    classe_choisie = st.selectbox("Classe", noms_classes, key="form_cahier_classe")
                    matiere_choisie = st.selectbox("Matière", noms_matieres)
                with col2:
                    date_cours = st.date_input("Date du cours", value=datetime.now().date())
                    duree_cours = st.selectbox(
                        "Durée de la séance",
                        options=[1.0, 2.0, 3.0, 4.0],
                        format_func=lambda x: f"{int(x)} heure{'s' if x > 1 else ''}",
                    )

                titre_cours = st.text_input("Titre / Intitulé du cours ou du devoir *", placeholder="Ex: Chapitre 1 - Les bases")
                contenu = st.text_area("Contenu détaillé de la séance / Travail à faire *", placeholder="Déroulement de la leçon...")
                
                with st.expander("➕ Options supplémentaires"):
                    difficultees = st.text_area("Difficultés particulières observées (optionnel)", placeholder="Remarques...")

                submitted = st.form_submit_button("💾 Enregistrer l'entrée dans la base", type="primary")
                
                if submitted:
                    if not titre_cours.strip() or not contenu.strip():
                        st.error("⚠️ Veuillez remplir le titre et le contenu détaillé de la séance.")
                    else:
                        cls_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
                        mat_obj = next(
                            (m for m in matieres_cycle if getattr(m, "libelle", None) == matiere_choisie or getattr(m, "nom", None) == matiere_choisie), 
                            None
                        )

                        contenu_formate = f"**[{titre_cours.strip()}]**\n{contenu.strip()}"
                        duree_str = f"{int(duree_cours)} heure{'s' if duree_cours > 1 else ''}"

                        nouvelle_entree = CahierTexte(
                            school_id=target_school_id,
                            cycle=cycle_en_cours,
                            classe_id=cls_obj.id if cls_obj else None,
                            matiere_id=mat_obj.id if mat_obj else None,
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

                        nouveau_log = ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.now(),
                            username=username,
                            action=f"Saisie Cahier de Texte : {matiere_choisie} ({duree_str}) - {titre_cours} ({classe_choisie})",
                            module="Cahier de Texte",
                            statut="Succès",
                        )
                        db.add(nouveau_log)
                        db.commit()

                        st.success(f"✅ Entrée enregistrée ({duree_str}) pour la classe **{classe_choisie}** en **{matiere_choisie}** !")
                        st.rerun()

    finally:
        db.close()


# Alias de compatibilité
afficher_cahier_de_texte = afficher_cahier_texte