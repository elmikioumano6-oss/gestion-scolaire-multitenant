import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Matiere, School, ActivityLog, CahierTexte

def afficher_cahier_texte():
    st.subheader("📖 Cahier de Texte Numérique")
    st.markdown("Suivi centralisé des cours dispensés, des contenus pédagogiques, des durées et des devoirs avec isolation multi-tenant et persistance en base de données.")
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
        # Cible de l'école pour le super admin si non défini
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        # Isolation multi-écoles et multi-cycles pour les classes et matières
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
            st.warning(f"⚠️ Veuillez vous assurer d'avoir enregistré des classes et des matières pour le cycle **{cycle_en_cours}**.")
            st.info("Utilisez les modules **Classes & Tarifs** et **Matières & Coeffs** du menu latéral pour les configurer.")
            return

        noms_classes = [c.libelle for c in classes_cycle]
        noms_matieres = [m.libelle for m in matieres_cycle]

        tab1, tab2 = st.tabs(["📖 Consulter le Cahier de Texte", "✍️ Saisir un Cours / Devoir (Enseignant ou Substitution Censeur)"])

        with tab1:
            st.markdown(f"### Entrées du Cahier de Texte — **{school_name} ({cycle_en_cours})**")
            classe_consult = st.selectbox("Sélectionner la classe à consulter", noms_classes, key="consult_cahier_classe")
            
            classe_obj = next((c for c in classes_cycle if c.libelle == classe_consult), None)
            
            if classe_obj:
                # Récupération directe depuis la base de données relationnelle
                entrees_db = db.query(CahierTexte).filter(
                    CahierTexte.school_id == target_school_id,
                    CahierTexte.classe_id == classe_obj.id
                ).order_by(CahierTexte.date.desc()).all()

                if not entrees_db:
                    st.info(f"Aucune entrée enregistrée pour la classe **{classe_consult}** dans le cycle **{cycle_en_cours}**.")
                else:
                    data_tableau = []
                    for e in entrees_db:
                        matiere_obj = db.query(Matiere).filter(Matiere.id == e.matiere_id).first()
                        nom_matiere = matiere_obj.libelle if matiere_obj else "Matière non spécifiée"
                        date_str = e.date.strftime('%d/%m/%Y') if e.date else "N/D"
                        duree_val = getattr(e, 'duree', 1.0)
                        
                        data_tableau.append({
                            "Date": date_str,
                            "Matière": nom_matiere,
                            "Durée": f"{duree_val}h",
                            "Auteur / Enseignant": e.enseignant_username or "Administration",
                            "Contenu Réalisé": e.contenu_realise,
                            "Difficultés": e.difficultees or "Aucune"
                        })

                    df_cahier = pd.DataFrame(data_tableau)
                    st.dataframe(df_cahier, use_container_width=True)

        with tab2:
            if role_utilisateur == "enseignant":
                st.markdown(f"### Espace Enseignant — Saisie de votre cours (**{username}**)")
            else:
                st.markdown(f"### Saisie / Substitution Censeur & Administration — **{school_name}**")
                st.info("💡 En tant que censeur, vous pouvez remplir ce cahier si l'enseignant vacataire n'a pas pu le faire.")

            with st.form("form_add_cahier_db"):
                col1, col2 = st.columns(2)
                with col1:
                    classe_choisie = st.selectbox("Classe", noms_classes, key="form_cahier_classe")
                    matiere_choisie = st.selectbox("Matière", noms_matieres)
                with col2:
                    date_cours = st.date_input("Date du cours", value=datetime.now().date())
                    duree_cours = st.selectbox("Durée de la séance", options=[1.0, 2.0, 3.0], format_func=lambda x: f"{int(x)} heure{'s' if x > 1 else ''}")
                
                titre_cours = st.text_input("Titre / Intitulé du cours ou du devoir")
                contenu = st.text_area("Contenu détaillé de la séance / Travail à faire *")
                difficultees = st.text_area("Difficultés particulières observées (optionnel)")

                submitted = st.form_submit_button("Enregistrer l'entrée dans la base", type="primary")
                if submitted:
                    if not titre_cours.strip() or not contenu.strip():
                        st.error("⚠️ Veuillez remplir le titre et le contenu détaillé de la séance.")
                    else:
                        cls_obj = next(c for c in classes_cycle if c.libelle == classe_choisie)
                        mat_obj = next(m for m in matieres_cycle if m.libelle == matiere_choisie)

                        # Formatage combiné du titre et du contenu
                        contenu_formate = f"**[{titre_cours.strip()}]**\n{contenu.strip()}"

                        # Enregistrement persistant dans la base de données SQL avec la durée
                        nouvelle_entree = CahierTexte(
                            school_id=target_school_id,
                            classe_id=cls_obj.id,
                            matiere_id=mat_obj.id,
                            enseignant_username=username,
                            date=datetime.combine(date_cours, datetime.now().time()),
                            contenu_realise=contenu_formate,
                            difficultees=difficultees.strip() if difficultees else None,
                            duree=duree_cours
                        )
                        db.add(nouvelle_entree)

                        # Traçabilité dans le journal d'activité (avec l'heure locale exacte)
                        nouveau_log = ActivityLog(
                            school_id=target_school_id,
                            timestamp=datetime.now(),
                            username=username,
                            action=f"Saisie Cahier de Texte : {matiere_choisie} ({duree_cours}h) - {titre_cours} ({classe_choisie})",
                            module="Cahier de Texte",
                            statut="Succès"
                        )
                        db.add(nouveau_log)
                        db.commit()

                        st.success(f"✅ Entrée enregistrée ({duree_cours}h) pour la classe **{classe_choisie}** en **{matiere_choisie}** !")
                        st.rerun()

    finally:
        db.close()

# Alias de compatibilité
afficher_cahier_de_texte = afficher_cahier_texte