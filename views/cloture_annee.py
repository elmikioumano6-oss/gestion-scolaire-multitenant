import streamlit as st
from database.db_config import SessionLocal
from database.models import AnneeScolaire, Eleve
from database.audit import log_action_erp

def afficher_cloture_annee():
    # --- Injection CSS ---
    st.markdown("""
        <style>
        .cloture-card {
            background: linear-gradient(135deg, #e11d48 0%, #be123c 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            border-left: 5px solid #f43f5e;
        }
        .cloture-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .cloture-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #ffe4e6; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="cloture-card">
            <div style="font-size: 3.5rem; margin-right: 25px;">⏳</div>
            <div>
                <h2>Transition d'Année Académique</h2>
                <p>Clôturez l'année en cours, archivez l'historique et préparez la nouvelle rentrée.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        annee_active = db.query(AnneeScolaire).filter(AnneeScolaire.active == True).first()
        libelle_actuel = annee_active.libelle if annee_active else "Aucune année active"

        st.info(f"📌 **Année académique actuellement active :** {libelle_actuel}")

        st.markdown("### ⚠️ Procédure de Fin d'Année (Rollover)")
        st.warning(
            "**Que fait exactement cette action ?**\n"
            "1. Elle clôture l'année scolaire actuelle de manière définitive.\n"
            "2. Elle crée et active la nouvelle année scolaire pour tout le système.\n"
            "3. Elle détache les élèves de leurs classes actuelles : ils passeront en statut 'En attente de réinscription' pour que vous puissiez les affecter dans leur classe supérieure lors du paiement de la nouvelle rentrée."
        )

        with st.form("form_cloture_annee"):
            st.markdown("#### Configuration de la nouvelle rentrée")
            col1, col2 = st.columns(2)
            
            with col1:
                st.text_input("Année à clôturer", value=libelle_actuel, disabled=True)
            with col2:
                # Suggestion intelligente pour l'année suivante (ex: 2026-2027 devient 2027-2028)
                sugg_nouvelle = ""
                if annee_active and "-" in libelle_actuel:
                    try:
                        parts = libelle_actuel.split("-")
                        sugg_nouvelle = f"{int(parts[0])+1}-{int(parts[1])+1}"
                    except:
                        sugg_nouvelle = "2027-2028"
                
                nouvelle_annee = st.text_input("Libellé de la nouvelle année *", value=sugg_nouvelle)

            st.markdown("---")
            confirmation = st.text_input(
                "Sécurité : Tapez 'CLOTURER' pour confirmer cette action irréversible", 
                placeholder="CLOTURER"
            )

            submit_cloture = st.form_submit_button("🚨 Exécuter la transition d'année", type="primary")

            if submit_cloture:
                if confirmation != "CLOTURER":
                    st.error("⚠️ Vous devez taper exactement 'CLOTURER' (en majuscules) pour déverrouiller et valider l'opération.")
                elif not nouvelle_annee.strip():
                    st.error("⚠️ Le libellé de la nouvelle année est obligatoire.")
                else:
                    try:
                        # 1. Désactiver l'ancienne année
                        if annee_active:
                            annee_active.active = False
                        else:
                            db.query(AnneeScolaire).update({AnneeScolaire.active: False})

                        # 2. Créer la nouvelle année
                        nouvelle_annee_obj = AnneeScolaire(
                            libelle=nouvelle_annee.strip(),
                            active=True
                        )
                        db.add(nouvelle_annee_obj)

                        # 3. Détacher les élèves de leurs classes pour exiger une réinscription
                        query_eleves = db.query(Eleve).filter(Eleve.deleted_at.is_(None))
                        if not is_super_admin:
                            query_eleves = query_eleves.filter(Eleve.school_id == school_id)
                        
                        nb_eleves_detaches = query_eleves.update({Eleve.classe_id: None}, synchronize_session=False)

                        # 4. Logger l'action critique
                        log_action_erp(
                            module="Clôture Année",
                            action=f"Clôture de {libelle_actuel} et ouverture de {nouvelle_annee.strip()}",
                            statut="Critique",
                            valeur_avant=libelle_actuel,
                            valeur_apres=nouvelle_annee.strip()
                        )

                        db.commit()
                        st.success(f"✅ Transition réussie ! L'année **{nouvelle_annee}** est désormais active sur la plateforme. {nb_eleves_detaches} élèves attendent leur réaffectation dans le menu d'inscription.")
                        st.rerun()

                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ Erreur technique lors de la clôture : {e}")

    finally:
        db.close()