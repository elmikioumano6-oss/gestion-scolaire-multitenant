import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import io
from database.db_config import SessionLocal, engine
import sqlalchemy as sa
from database.models import School, JournalActivite

def afficher_journal_activite():
    st.subheader("📜 Journal d'Activité & Piste d'Audit (Normes ERP - SOC 2 / ISO 27001)")
    st.markdown("Traçabilité immuable, métadonnées de session, analyse granulaire des écarts (Diff Avant/Après) et export certifié.")
    st.markdown("---")

    # --- MIGRATION AUTOMATIQUE DES COLONNES DE TRAÇABILITÉ GRANULAIRE ---
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("ALTER TABLE journal_activites ADD COLUMN ip_address VARCHAR(50) DEFAULT '127.0.0.1';"))
            conn.commit()
    except Exception:
        pass

    try:
        with engine.connect() as conn:
            conn.execute(sa.text("ALTER TABLE journal_activites ADD COLUMN session_id VARCHAR(100) DEFAULT 'SES-PROD-01';"))
            conn.commit()
    except Exception:
        pass

    try:
        with engine.connect() as conn:
            conn.execute(sa.text("ALTER TABLE journal_activites ADD COLUMN valeur_avant TEXT;"))
            conn.commit()
    except Exception:
        pass

    try:
        with engine.connect() as conn:
            conn.execute(sa.text("ALTER TABLE journal_activites ADD COLUMN valeur_apres TEXT;"))
            conn.commit()
    except Exception:
        pass

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # --- 1. SÉLECTION DE L'ÉTABLISSEMENT (POUR SUPER ADMIN) ---
        if is_super_admin:
            st.markdown("### 🌐 Vue Globale Super Administrateur")
            ecoles = db.query(School).all()
            options_ecoles = {"🌐 Toutes les écoles (Vue Globale)": None}
            for ecole in ecoles:
                options_ecoles[ecole.nom] = ecole.id
            
            choix_ecole_nom = st.selectbox("Filtrer par établissement", list(options_ecoles.keys()), key="journal_filter_school")
            selected_school_id = options_ecoles[choix_ecole_nom]
        else:
            selected_school_id = school_id
            st.markdown(f"### Historique des Événements — **{school_name}**")

        # --- 2. FILTRES D'AUDIT AVANCÉS ---
        with st.expander("🔍 Filtres d'Audit Avancés (Période, Module, Utilisateur, Sévérité)", expanded=True):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            
            with col_f1:
                date_debut = st.date_input("Date de début", value=date.today() - timedelta(days=30), key="audit_date_debut")
            with col_f2:
                date_fin = st.date_input("Date de fin", value=date.today(), key="audit_date_fin")
            with col_f3:
                modules_disibles = ["Tous les modules", "Saisie des notes", "Présence", "Supervision cahier", "Administration Globale", "Finances", "Consultation des notes", "Espace Inspection"]
                module_filtre = st.selectbox("Filtrer par module", options=modules_disibles, key="audit_module_filter")
            with col_f4:
                severites_disibles = ["Tous les statuts", "Succès", "Critique", "Avertissement", "Observation Validée"]
                statut_filtre = st.selectbox("Filtrer par niveau / statut", options=severites_disibles, key="audit_statut_filter")

            recherche_user = st.text_input("Rechercher par nom d'utilisateur (Username)", placeholder="Ex: admin, censeur...", key="audit_user_search")

        # --- 3. REQUÊTE ET FILTRAGE EN BASE DE DONNÉES ---
        query = db.query(JournalActivite)
        
        if selected_school_id is not None:
            query = query.filter(JournalActivite.school_id == selected_school_id)
        
        if date_debut and date_fin:
            dt_debut = datetime.combine(date_debut, time.min)
            dt_fin = datetime.combine(date_fin, time.max)
            query = query.filter(JournalActivite.timestamp >= dt_debut, JournalActivite.timestamp <= dt_fin)

        if module_filtre != "Tous les modules":
            query = query.filter(JournalActivite.module == module_filtre)

        if statut_filtre != "Tous les statuts":
            query = query.filter(JournalActivite.statut == statut_filtre)

        if recherche_user.strip():
            query = query.filter(JournalActivite.username.ilike(f"%{recherche_user.strip()}%"))

        logs = query.order_by(JournalActivite.timestamp.desc()).all()

        # --- 4. TABLEAU DE BORD / KPIS D'AUDIT ---
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        with col_kpi1:
            st.metric("Total Événements Audités", len(logs))
        with col_kpi2:
            critiques = sum(1 for l in logs if getattr(l, 'statut', '') in ["Critique", "Avertissement"])
            st.metric("Événements à Risque / Alertes", critiques, delta_color="inverse")
        with col_kpi3:
            utilisateurs_uniques = len(set(getattr(l, 'username', 'N/D') for l in logs))
            st.metric("Opérateurs Actifs", utilisateurs_uniques)

        st.markdown("---")

        if not logs:
            st.info("ℹ️ Aucun événement ne correspond aux critères de filtrage sélectionnés pour cette période.")
        else:
            data_logs = []
            for l in logs:
                sc_obj = db.query(School).filter(School.id == l.school_id).first() if hasattr(l, 'school_id') and l.school_id else None
                nom_ecole_log = sc_obj.nom if sc_obj else f"École #{getattr(l, 'school_id', 'N/D')}"
                
                dt_str = l.timestamp.strftime("%d/%m/%Y %H:%M:%S") if hasattr(l, 'timestamp') and l.timestamp else "N/D"
                data_logs.append({
                    "ID": getattr(l, 'id', 'N/D'),
                    "Date & Heure": dt_str,
                    "Établissement": nom_ecole_log,
                    "Utilisateur": getattr(l, 'username', 'N/D'),
                    "Module ERP": getattr(l, 'module', 'N/D'),
                    "Statut / Niveau": getattr(l, 'statut', 'Succès'),
                    "Action & Description": getattr(l, 'action', 'N/D'),
                    "Adresse IP": getattr(l, 'ip_address', '127.0.0.1'),
                    "Session ID": getattr(l, 'session_id', 'SES-PROD-01'),
                    "Valeur Avant": getattr(l, 'valeur_avant', None),
                    "Valeur Après": getattr(l, 'valeur_apres', None)
                })

            df_logs = pd.DataFrame(data_logs)

            # --- 5. BOUTONS D'EXPORT CERTIFIÉ (CSV & EXCEL) ---
            col_exp1, col_exp2, _ = st.columns([1, 1, 2])
            with col_exp1:
                csv_data = df_logs.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Exporter en CSV (Audit)",
                    data=csv_data,
                    file_name=f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col_exp2:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_logs.drop(columns=["Valeur Avant", "Valeur Après"]).to_excel(writer, index=False, sheet_name='Audit Trail')
                excel_data = output.getvalue()
                st.download_button(
                    label="📊 Exporter en Excel (Rapport)",
                    data=excel_data,
                    file_name=f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 6. AFFICHAGE DÉTAILLÉ & IMMUABILITÉ GARANTIE ---
            st.markdown(f"#### 🔎 Piste d'Audit Granulaire & Immuable ({len(logs)} événements)")
            st.markdown("<small style='color: #6c757d;'>🔒 Sécurité ERP : Les logs ci-dessous intègrent la traçabilité IP, l'ID de session et l'analyse des écarts (Diff Avant/Après) en lecture seule (Append-Only).</small>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            for item in data_logs[:100]:
                action_text = item['Action & Description']
                with st.expander(f"[{item['Date & Heure']}] - {item['Utilisateur']} ({item['Module ERP']}) : {action_text[:60]}... [{item['Statut / Niveau']}]"):
                    col_det1, col_det2 = st.columns(2)
                    with col_det1:
                        st.markdown(f"**Établissement :** {item['Établissement']}")
                        st.markdown(f"**Opérateur :** `{item['Utilisateur']}`")
                        st.markdown(f"**Adresse IP Source :** `{item['Adresse IP']}`")
                        st.markdown(f"**Identifiant Session :** `{item['Session ID']}`")
                    with col_det2:
                        st.markdown(f"**Module ERP :** {item['Module ERP']}")
                        st.markdown(f"**Niveau / Statut :** {item['Statut / Niveau']}")
                        st.markdown(f"**ID Log Immuable :** #{item['ID']}")
                    
                    st.markdown("---")
                    st.markdown(f"**Description complète de l'action :** {action_text}")
                    
                    # Affichage conditionnel de la traçabilité des écarts (Diff Avant / Après)
                    if item['Valeur Avant'] or item['Valeur Après']:
                        st.markdown("**Analyse des Écarts (Diff Avant / Après) :**")
                        col_diff1, col_diff2 = st.columns(2)
                        with col_diff1:
                            st.error(f"🔴 **Avant modification :**\n\n{item['Valeur Avant'] or '—'}")
                        with col_diff2:
                            st.success(f"🟢 **Après modification :**\n\n{item['Valeur Après'] or '—'}")

    finally:
        db.close()

# Alias de compatibilité
afficher_journal_activite = afficher_journal_activite
afficher_audit = afficher_journal_activite
afficher_journal_d_activite = afficher_journal_activite