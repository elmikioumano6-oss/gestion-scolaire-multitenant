import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_config import SessionLocal
from database.models import Classe, Eleve, Presence, School, ActivityLog

def afficher_presence():
    st.subheader("📋 Gestion Avancée des Présences & Assiduité")
    st.markdown("Suivi des présences en temps réel, traçabilité des intervenants, des séances et des motifs d'absence avec persistance en base de données.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    role_utilisateur = str(st.session_state.get("role", "")).lower()
    username = st.session_state.get("username", "admin")
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

        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
        else:
            school_name = st.session_state.get("school_name", "Établissement")

        # Isolation stricte multi-écoles et multi-cycles pour les classes
        classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
        if not is_super_admin and school_id:
            classes_query = classes_query.filter(Classe.school_id == school_id)
        else:
            classes_query = classes_query.filter(Classe.school_id == target_school_id)
        classes_cycle = classes_query.all()

        st.markdown(f"### Suivi des Présences — **{school_name} ({cycle_en_cours})**")

        if not classes_cycle:
            st.warning(f"⚠️ Aucune classe configurée pour le cycle **{cycle_en_cours}** dans l'établissement **{school_name}**.")
            st.info("Veuillez d'abord enregistrer vos classes dans le module **Classes & Tarifs** du menu latéral.")
            return

        noms_classes = [c.libelle for c in classes_cycle]

        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            classe_choisie = st.selectbox("Sélectionner la classe", noms_classes, key="presence_classe_select")
        with col_sel2:
            date_appel = st.date_input("Date de l'appel", value=datetime.now().date(), key="presence_date_select")
        
        classe_obj = next((c for c in classes_cycle if c.libelle == classe_choisie), None)
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id)
            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            else:
                eleves_query = eleves_query.filter(Eleve.school_id == target_school_id)
            eleves = eleves_query.order_by(Eleve.nom).all()

            if not eleves:
                st.info(f"Aucun élève inscrit dans la classe **{classe_choisie}**.")
            else:
                if role_utilisateur == "enseignant":
                    st.info(f"👨‍🏫 Espace Enseignant — Feuille d'appel active pour la classe de **{classe_choisie}** ({len(eleves)} élèves).")
                else:
                    st.info(f"📐 Espace Censeur / Administration — Feuille d'appel active (Substitution) pour **{classe_choisie}** ({len(eleves)} élèves).")

                # Récupérer les présences déjà enregistrées pour cette date et cette classe
                existantes = db.query(Presence).join(Eleve).filter(
                    Presence.school_id == target_school_id,
                    Presence.date == date_appel,
                    Eleve.classe_id == classe_obj.id
                ).all()
                dict_existantes = {p.eleve_id: p for p in existantes}

                data_appel = []
                for e in eleves:
                    p_ex = dict_existantes.get(e.id)
                    statut_defaut = p_ex.statut if p_ex else "Présent"
                    motif_defaut = p_ex.motif if p_ex and p_ex.motif else ""
                    
                    data_appel.append({
                        "eleve_id": e.id,
                        "Matricule": e.matricule,
                        "Nom & Prénom": f"{e.nom} {e.prenom}",
                        "Statut": statut_defaut,
                        "Motif": motif_defaut
                    })

                df_appel = pd.DataFrame(data_appel)
                
                # Éditeur de tableau interactif pour l'appel
                edited_df = st.data_editor(
                    df_appel,
                    column_config={
                        "eleve_id": None,  # Masqué dans l'UI
                        "Matricule": st.column_config.TextColumn("Matricule", disabled=True),
                        "Nom & Prénom": st.column_config.TextColumn("Nom & Prénom", disabled=True),
                        "Statut": st.column_config.SelectboxColumn(
                            "Statut",
                            options=["Présent", "Absent", "Retard"],
                            required=True
                        ),
                        "Motif": st.column_config.TextColumn("Motif (si absent ou retard)")
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_presence_{classe_choisie}_{date_appel}"
                )
                
                if st.button("💾 Enregistrer l'appel en base de données", type="primary"):
                    # Nettoyage des anciennes entrées pour cette date et cette classe pour éviter les doublons
                    eleve_ids = [row["eleve_id"] for _, row in edited_df.iterrows()]
                    db.query(Presence).filter(
                        Presence.school_id == target_school_id,
                        Presence.date == date_appel,
                        Presence.eleve_id.in_(eleve_ids)
                    ).delete(synchronize_session=False)

                    # Enregistrement des nouveaux statuts de présence
                    for _, row in edited_df.iterrows():
                        nouvelle_presence = Presence(
                            school_id=target_school_id,
                            eleve_id=row["eleve_id"],
                            date=date_appel,
                            statut=row["Statut"],
                            motif=row["Motif"].strip() if row["Motif"] else None
                        )
                        db.add(nouvelle_presence)

                    # Traçabilité dans le journal d'activité
                    nouveau_log = ActivityLog(
                        school_id=target_school_id,
                        timestamp=datetime.now(),
                        username=username,
                        action=f"Validation appel des présences - Classe {classe_choisie} ({date_appel}) par {username}",
                        module="Présence",
                        statut="Succès"
                    )
                    db.add(nouveau_log)
                    db.commit()

                    st.success(f"✅ Registre des présences enregistré et sauvegardé avec succès pour la classe **{classe_choisie}** au {date_appel.strftime('%d/%m/%Y')} !")
                    st.rerun()

    finally:
        db.close()

# Alias de compatibilité
afficher_gestion_presence = afficher_presence
afficher_presence = afficher_presence