import streamlit as st
import pandas as pd
from database.db_config import SessionLocal
from database.models import Eleve, Classe, User, School, Paiement, Depense, JournalActivite
from sqlalchemy import func, desc, or_, and_

def afficher_accueil():
    # --- 1. RÉCUPÉRATION DYNAMIQUE DE L'ÉCOLE ACTIVE ---
    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username = st.session_state.get("username", "")

    # 🔒 Confinement strict de l'admin Rahmat
    if username and "rahmat" in username.lower():
        is_super_admin = False

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

        # --- 2. EN-TÊTE INSTITUTIONNEL ÉPURÉ ---
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

        st.subheader("📊 Tableau de Bord ERP & Pilotage Exécutif")
        st.markdown("Synthèse analytique en temps réel : indicateurs académiques, santé financière et flux d'audit de sécurité.")
        st.markdown("---")

        # --- 3. FILTRAGE DES DONNÉES (AVEC SOFT DELETE) ---
        q_eleves = db.query(Eleve).filter(Eleve.deleted_at.is_(None))
        q_classes = db.query(Classe).filter(Classe.deleted_at.is_(None))
        q_users = db.query(User)
        
        if not is_super_admin and school_id:
            q_eleves = q_eleves.filter(Eleve.school_id == school_id)
            q_classes = q_classes.filter(Classe.school_id == school_id)
            q_users = q_users.filter(User.school_id == school_id)

        total_eleves = q_eleves.count()
        total_classes = q_classes.count()
        total_utilisateurs = q_users.count()
        total_profs = q_users.filter(User.role == 'prof').count() if hasattr(User, 'role') else 0

        # --- CALCULS FINANCIERS (RECETTES, DÉPENSES, SOLDE NET) ---
        q_paiements = db.query(Paiement)
        q_depenses = db.query(Depense)
        
        if not is_super_admin and school_id:
            q_paiements = q_paiements.filter(Paiement.school_id == school_id)
            q_depenses = q_depenses.filter(Depense.school_id == school_id)

        total_recettes = q_paiements.with_entities(func.sum(Paiement.montant)).scalar() or 0.0
        total_depenses = q_depenses.with_entities(func.sum(Depense.montant)).scalar() or 0.0
        solde_net = float(total_recettes) - float(total_depenses)
        
        total_attendu = total_eleves * 65000  
        taux_recouvrement = (total_recettes / total_attendu * 100) if total_attendu > 0 else 0.0

        # --- 4. INDICATEURS CLÉS DE PERFORMANCE (KPIs) ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👨‍🎓 Élèves Actifs", f"{total_eleves}", delta="Inscrits")
        with col2:
            st.metric("👩‍🏫 Corps Professoral", f"{total_profs if total_profs > 0 else 'N/D'}", delta="Enseignants")
        with col3:
            st.metric("🏫 Classes Actives", f"{total_classes}", delta="Pédagogie")
        with col4:
            st.metric("👤 Comptes Utilisateurs", f"{total_utilisateurs}", delta="Sécurité")

        st.markdown("---")

        # --- 5. SECTION FINANCIÈRE & RÉPARTITION ---
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            st.markdown("### 💰 Santé Financière & Trésorerie")
            
            st.metric("🟢 Recettes Globales", f"{total_recettes:,.0f} FCFA")
            st.metric("🔴 Dépenses Opérationnelles", f"- {total_depenses:,.0f} FCFA")
            st.metric("💶 Solde Net en Caisse", f"{solde_net:,.0f} FCFA", delta="Disponible", delta_color="normal" if solde_net >= 0 else "inverse")
            
            st.markdown("Progression annuelle des encaissements :")
            st.progress(min(max(int(taux_recouvrement), 0), 100) / 100.0)

        with col_f2:
            st.markdown("### 📈 Répartition des Effectifs par Classe")
            classes_list = q_classes.all()
            
            if classes_list:
                effectifs_data = []
                for c in classes_list:
                    nom_c = getattr(c, 'libelle', getattr(c, 'nom', f"Classe {c.id}"))
                    nb_e = db.query(Eleve).filter(Eleve.classe_id == c.id, Eleve.deleted_at.is_(None)).count()
                    effectifs_data.append({"Classe": nom_c, "Élèves": nb_e})
                
                df_eff = pd.DataFrame(effectifs_data)
                st.bar_chart(df_eff.set_index("Classe"))
            else:
                st.info("Aucune classe enregistrée pour générer le graphique.")

        st.markdown("---")

        # --- 6. FLUX D'AUDIT DE SÉCURITÉ & RACCOURCIS ---
        col_a1, col_a2 = st.columns([1.5, 1])
        
        with col_a1:
            st.markdown("### 🛡️ Journal d'Activité (Actions Récentes)")
            
            q_logs = db.query(JournalActivite)
            
            # 🔒 HIÉRARCHIE RBAC & MULTI-TENANT STRICTE :
            # 1. Super Admin : Voit tout.
            # 2. Admin d'école (ex: admin_rahmat) : Voit tous les logs de son école (tous ses utilisateurs rattachés), 
            #    mais les utilisateurs subordonnés ne voient que leurs propres actions.
            if is_super_admin:
                pass 
            else:
                user_obj = db.query(User).filter(User.username == username).first()
                user_role = getattr(user_obj, 'role', '').lower() if user_obj else ''
                is_school_admin = user_role in ["admin", "directeur", "proviseur", "censeur"] or "admin" in username.lower()
                
                if is_school_admin and school_id:
                    # L'admin de l'école voit toute l'activité de son établissement, sans les logs globaux du super admin
                    q_logs = q_logs.filter(
                        and_(
                            JournalActivite.username != "admin",
                            JournalActivite.school_id == school_id
                        )
                    )
                else:
                    # Un utilisateur standard ne voit que ses propres actions
                    q_logs = q_logs.filter(JournalActivite.username == username)
                
            derniers_logs = q_logs.order_by(desc(JournalActivite.timestamp)).limit(5).all()
            
            if derniers_logs:
                for log in derniers_logs:
                    heure = log.timestamp.strftime("%H:%M") if log.timestamp else "N/D"
                    couleur_statut = "#EF4444" if getattr(log, 'statut', '') in ["Critique", "Avertissement"] else "#10B981"
                    
                    st.markdown(
                        f"""
                        <div style="border-left: 3px solid {couleur_statut}; padding-left: 10px; margin-bottom: 8px; background-color: rgba(255,255,255,0.02); padding: 8px; border-radius: 4px;">
                            <span style="color: #94A3B8; font-size: 0.85rem;">{heure}</span> - 
                            <b>{log.username}</b> 
                            <span style="color: {couleur_statut}; font-size: 0.85rem; padding: 2px 6px; border-radius: 10px; border: 1px solid {couleur_statut}40; margin-left: 5px;">{log.module}</span><br>
                            <span style="font-size: 0.95rem;">{log.action}</span>
                        </div>
                        """, unsafe_allow_html=True
                    )
            else:
                st.info("Aucune activité récente enregistrée dans le journal d'audit pour cet établissement.")

        with col_a2:
            st.markdown("### ⚡ Raccourcis Opérationnels")
            if st.button("➕ Inscription Élève", use_container_width=True):
                st.info("Utilisez le menu latéral 'Inscription Élèves'.")
            if st.button("📝 Saisie des Notes", use_container_width=True):
                st.info("Utilisez le menu latéral 'Saisie des notes'.")
            if st.button("💵 Encaissement", use_container_width=True):
                st.info("Utilisez le menu latéral 'Encaissement'.")
            if st.button("📉 Saisir une Dépense", use_container_width=True):
                st.info("Utilisez le menu latéral 'Gestion des Dépenses'.")

    finally:
        db.close()

# Alias de compatibilité
afficher_accueil = afficher_accueil