from datetime import datetime
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import CahierTexte, Classe, Enseignant, Matiere, School, User

def afficher_cahier_texte():
    st.markdown("## 📖 Cahier de Texte Numérique")
    st.markdown("Suivi centralisé des cours dispensés, des contenus pédagogiques, des durées et des devoirs.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    role_utilisateur = str(st.session_state.get("role", "")).lower()
    username = st.session_state.get("username", "admin")
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

        # 1. Chargement global en une seule requête (zéro requête dans les boucles)
        classes_cycle = db.query(Classe).filter(Classe.cycle == cycle_en_cours, Classe.school_id == target_school_id).all()
        if not classes_cycle:
            st.warning(f"⚠️ Veuillez configurer des classes pour le cycle **{cycle_en_cours}**.")
            return

        noms_classes = [c.libelle for c in classes_cycle]

        # Dictionnaires de correspondance en mémoire pour un affichage instantané
        tous_enseignants = db.query(Enseignant).filter(Enseignant.school_id == target_school_id).all()
        dict_ens_options = {f"{e.nom} {e.prenom}".strip(): e.id for e in tous_enseignants}
        dict_ens_par_id = {e.id: f"{e.nom} {e.prenom}".strip() for e in tous_enseignants}

        toutes_matieres = db.query(Matiere).filter(Matiere.school_id == target_school_id).all()
        dict_mat_par_id = {m.id: (m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "Matière")) for m in toutes_matieres}

        tab1, tab2 = st.tabs([
            "📖 Consulter le Cahier de Texte",
            "✍️ Saisir un Cours / Devoir",
        ])

        with tab1:
            st.markdown(f"<h4 class='tab-title'>Entrées du Cahier de Texte — {cycle_en_cours}</h4>", unsafe_allow_html=True)
            classe_consult = st.selectbox("Sélectionner la classe à consulter", noms_classes, key="consult_cahier_classe")

            classe_obj = next((c for c in classes_cycle if c.libelle == classe_consult), None)
            if classe_obj:
                # Requête unique et directe filtrée par classe
                entrees_db = (
                    db.query(CahierTexte)
                    .filter(
                        CahierTexte.school_id == target_school_id,
                        CahierTexte.classe_id == classe_obj.id
                    )
                    .order_by(CahierTexte.date_cours.desc(), CahierTexte.id.desc())
                    .all()
                )

                if not entrees_db:
                    st.info(f"Aucune entrée enregistrée pour la classe {classe_consult}.")
                else:
                    for e in entrees_db:
                        nom_matiere = dict_mat_par_id.get(e.matiere_id, "Matière")
                        
                        nom_enseignant_affiche = e.auteur_saisie or "Administration"
                        if hasattr(e, "enseignant_id") and e.enseignant_id in dict_ens_par_id:
                            nom_enseignant_affiche = dict_ens_par_id[e.enseignant_id]

                        date_str = e.date_cours.strftime("%d/%m/%Y %H:%M") if isinstance(e.date_cours, datetime) else (str(e.date_cours) if e.date_cours else "N/D")
                        duree_val = getattr(e, "duree_seance", "1 heure")
                        titre = e.titre or 'Séance sans titre'

                        with st.expander(f"{date_str} — {nom_matiere.title()} ({duree_val}) | {titre}"):
                            st.write(f"**Enseignant(e) :** {nom_enseignant_affiche}")
                            st.write(f"**Contenu :**")
                            st.write(e.contenu)

                            if est_admin:
                                st.markdown("---")
                                if st.button("🗑️ Supprimer la séance", key=f"btn_delete_seance_{e.id}", type="secondary"):
                                    try:
                                        db.delete(e)
                                        db.commit()
                                        st.success("✅ Séance supprimée avec succès !")
                                        st.rerun()
                                    except Exception as err:
                                        db.rollback()
                                        st.error(f"Erreur : {err}")

        with tab2:
            st.markdown("#### Saisie de Cours")
            col1, col2 = st.columns(2)
            with col1:
                classe_choisie = st.selectbox("Classe", noms_classes, key="form_cahier_classe")
                classe_obj_s = next((c for c in classes_cycle if c.libelle == classe_choisie), None)

                noms_mat_classe = [m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "Matière") for m in toutes_matieres if not classe_obj_s or m.classe_id == classe_obj_s.id]
                if not noms_mat_classe:
                    noms_mat_classe = [m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "Matière") for m in toutes_matieres]
                
                matiere_choisie = st.selectbox("Matière", sorted(list(set(noms_mat_classe))) if noms_mat_classe else ["Aucune matière"], key="form_cahier_matiere")
            with col2:
                date_cours = st.date_input("Date du cours", value=datetime.now().date(), key="form_cahier_date")
                duree_cours = st.selectbox("Durée de la séance", options=[1.0, 2.0, 3.0, 4.0], format_func=lambda x: f"{int(x)} heure{'s' if x > 1 else ''}", key="form_cahier_duree")

            liste_noms_ens = list(dict_ens_options.keys())
            enseignant_nom_selectionne = st.selectbox(
                "Enseignant dispensant le cours *",
                options=liste_noms_ens,
                key="form_cahier_enseignant_libre",
            )
            enseignant_id_final = dict_ens_options.get(enseignant_nom_selectionne)

            titre_cours = st.text_input("Titre du cours *", key="form_cahier_titre")
            contenu = st.text_area("Contenu détaillé de la séance *", key="form_cahier_contenu")

            if st.button("💾 Enregistrer l'entrée dans la base", type="primary", key="form_cahier_submit"):
                if not titre_cours.strip() or not contenu.strip():
                    st.error("⚠️ Veuillez remplir le titre et le contenu détaillé.")
                elif not enseignant_id_final:
                    st.error("⚠️ Veuillez sélectionner l'enseignant.")
                else:
                    mat_obj = next((m for m in toutes_matieres if (m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "")).strip().title() == matiere_choisie.strip().title()), None)

                    # --- PROTECTION ANTI-DOUBLON STRICTE (Date + Classe + Matière) ---
                    entrees_existantes = db.query(CahierTexte).filter(
                        CahierTexte.school_id == target_school_id,
                        CahierTexte.classe_id == (classe_obj_s.id if classe_obj_s else None),
                        CahierTexte.matiere_id == (mat_obj.id if mat_obj else None)
                    ).all()

                    doublon_trouve = False
                    for ent in entrees_existantes:
                        date_ent_obj = ent.date_cours.date() if isinstance(ent.date_cours, datetime) else None
                        if date_ent_obj == date_cours:
                            doublon_trouve = True
                            break

                    if doublon_trouve:
                        st.error("⚠️ Un cours pour cette même matière et cette même classe a déjà été enregistré à cette date. Impossible de créer un doublon.")
                    else:
                        nouvelle_entree = CahierTexte(
                            school_id=target_school_id,
                            cycle=cycle_en_cours,
                            classe_id=classe_obj_s.id if classe_obj_s else None,
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