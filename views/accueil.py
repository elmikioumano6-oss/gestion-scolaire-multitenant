import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Eleve, Classe, User, School
from sqlalchemy import inspect

def afficher_accueil():
    # --- 1. RÉCUPÉRATION DYNAMIQUE DE L'ÉCOLE ACTIVE ---
    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    db = SessionLocal()
    try:
        nom_ecole = "Plateforme Scolaire"
        devise_ecole = "Excellence - Travail - Succès"
        adresse_ecole = "Quartier, Niamey - Niger"
        contacts_ecole = "N/D"

        if school_id:
            ecole = db.query(School).filter(School.id == school_id).first()
            if ecole:
                nom_ecole = ecole.nom
                devise_ecole = ecole.devise or "Excellence - Travail - Succès"
                adresse_ecole = getattr(ecole, 'adresse', "Quartier, Niamey - Niger")
                contacts_ecole = getattr(ecole, 'contacts', "N/D")

        # --- 2. EN-TÊTE INSTITUTIONNEL ÉPURÉ (SANS DOUBLE LOGO) ---
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); padding: 25px; border-radius: 12px; border-left: 6px solid #D97706; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 25px;">
                <h1 style="color: #FFFFFF; font-size: 1.8rem; font-weight: 800; margin: 0 0 8px 0;">🏫 {nom_ecole}</h1>
                <p style="color: #FBBF24; font-size: 1.05rem; font-weight: 600; margin: 0 0 12px 0;">Devise : {devise_ecole}</p>
                <p style="color: #94A3B8; font-size: 0.9rem; margin: 0;">📍 <b>Adresse / Quartier :</b> {adresse_ecole} | 📞 <b>Contacts :</b> {contacts_ecole}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.subheader("📊 Tableau de Bord Général & Pilotage Exécutif")
        st.markdown("Synthèse globale des indicateurs administratifs, pédagogiques et financiers de l'établissement.")
        st.markdown("---")

        # --- 3. FILTRAGE DES DONNÉES PAR SCHOOL_ID ---
        if is_super_admin:
            total_eleves = db.query(Eleve).count()
            total_classes = db.query(Classe).count()
            total_profs = db.query(User).filter(User.role == 'prof').count() if hasattr(User, 'role') else 0
            total_utilisateurs = db.query(User).count()
        else:
            total_eleves = db.query(Eleve).filter(Eleve.school_id == school_id).count() if school_id else 0
            total_classes = db.query(Classe).filter(Classe.school_id == school_id).count() if school_id else 0
            total_profs = db.query(User).filter(User.school_id == school_id, User.role == 'prof').count() if school_id and hasattr(User, 'role') else 0
            total_utilisateurs = db.query(User).filter(User.school_id == school_id).count() if school_id else 0

        total_recettes = 0.0
        total_attendu = total_eleves * 65000  
        
        if school_id:
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            for t_name in tables:
                if 'paiement' in t_name.lower() or 'encaissement' in t_name.lower():
                    try:
                        df_p = pd.read_sql(f"SELECT SUM(montant) as total FROM {t_name}", con=db.bind)
                        if not df_p.empty and df_p['total'].iloc[0] is not None:
                            total_recettes = float(df_p['total'].iloc[0])
                    except Exception:
                        pass

        taux_recouvrement = (total_recettes / total_attendu * 100) if total_attendu > 0 else 0.0

        # --- 4. INDICATEURS CLÉS DE PERFORMANCE (KPIs) ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👨‍🎓 Total Élèves Inscrits", f"{total_eleves}", delta="Actifs")
        with col2:
            st.metric("👩‍🏫 Corps Professoral", f"{total_profs if total_profs > 0 else 'N/D'}", delta="Enseignants")
        with col3:
            st.metric("🏫 Classes Actives", f"{total_classes}", delta="Pédagogie")
        with col4:
            st.metric("👤 Comptes Utilisateurs", f"{total_utilisateurs}", delta="Sécurité")

        st.markdown("---")

        # --- 5. SECTION FINANCIÈRE & ANALYTIQUE ---
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            st.markdown("### 💰 Synthèse Trésorerie & Recouvrement")
            st.metric("Recettes Globales Encaissées", f"{total_recettes:,.0f} FCFA", delta=f"Taux global : {taux_recouvrement:.1f}%")
            
            st.markdown("Progression annuelle des encaissements :")
            st.progress(min(max(int(taux_recouvrement), 0), 100) / 100.0)

            st.markdown("""
                <div style="background: rgba(217, 119, 6, 0.1); border-left: 4px solid #D97706; padding: 12px; border-radius: 6px; margin-top: 15px;">
                    <small style="color: #FBBF24; font-weight: 600;">ℹ️ Conseil de gestion :</small><br>
                    <span style="color: #E2E8F0; font-size: 0.85rem;">Surveillez régulièrement le module 'Soldes & Impayés' pour maintenir un taux de recouvrement optimal au sein de l'établissement.</span>
                </div>
            """, unsafe_allow_html=True)

        with col_f2:
            st.markdown("### 📈 Répartition des Effectifs par Classe")
            if school_id or is_super_admin:
                query_classes = db.query(Classe)
                if not is_super_admin and school_id:
                    query_classes = query_classes.filter(Classe.school_id == school_id)
                classes_list = query_classes.all()
                
                if classes_list:
                    effectifs_data = []
                    for c in classes_list:
                        nom_c = getattr(c, 'libelle', getattr(c, 'nom', f"Classe {c.id}"))
                        nb_e = db.query(Eleve).filter(Eleve.classe_id == c.id).count()
                        effectifs_data.append({"Classe": nom_c, "Élèves": nb_e})
                    
                    df_eff = pd.DataFrame(effectifs_data)
                    st.bar_chart(df_eff.set_index("Classe"))
                else:
                    st.info("Aucune classe enregistrée pour générer le graphique.")
            else:
                st.info("Veuillez sélectionner un établissement.")

        st.markdown("---")

        # --- 6. ACCÈS RAPIDE AUX MODULES STRATÉGIQUES ---
        st.markdown("### ⚡ Raccourcis Opérationnels Fréquents")
        
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            if st.button("➕ Inscription Élève", use_container_width=True):
                st.info("Utilisez le menu latéral 'Inscription Élèves'.")
        with col_r2:
            if st.button("📝 Saisie des Notes", use_container_width=True):
                st.info("Utilisez le menu latéral 'Saisie des notes'.")
        with col_r3:
            if st.button("💵 Encaissement", use_container_width=True):
                st.info("Utilisez le menu latéral 'Encaissement'.")
        with col_r4:
            if st.button("💬 Centre Messages", use_container_width=True):
                st.info("Utilisez le menu latéral 'Messages'.")

    finally:
        db.close()