from datetime import datetime, date, time, timedelta
import io
import sqlalchemy as sa
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal, engine
from database.models import School, JournalActivite, User
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

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
    username_connecte = st.session_state.get("username", "")
    role_connecte = st.session_state.get("role", "").lower()

    # 🔒 Confinement strict de l'admin Rahmat
    if username_connecte and "rahmat" in username_connecte.lower():
        is_super_admin = False

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # --- 1. SÉLECTION DE L'ÉTABLISSEMENT (RESTRICTION STRICTE MULTI-TENANT) ---
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

        # --- 3. REQUÊTE ET FILTRAGE EN BASE DE DONNÉES (HIÉRARCHIE STRICTE RBAC) ---
        query = db.query(JournalActivite)
        
        if is_super_admin:
            # Le Super Admin voit tout (avec filtre optionnel par selectbox)
            if selected_school_id is not None:
                query = query.filter(JournalActivite.school_id == selected_school_id)
        else:
            # Vérification exacte du rôle de l'utilisateur en base ou session
            user_obj = db.query(User).filter(User.username == username_connecte).first()
            user_role = getattr(user_obj, 'role', '').lower() if user_obj else role_connecte
            is_school_admin = user_role in ["admin", "directeur", "proviseur", "censeur"] or "admin" in username_connecte.lower()
            
            if school_id:
                if is_school_admin:
                    # L'administrateur de l'école voit tous les logs de son école, sans les actions globales du super admin "admin"
                    query = query.filter(
                        sa.and_(
                            JournalActivite.username != "admin",
                            JournalActivite.school_id == school_id
                        )
                    )
                else:
                    # Un utilisateur standard ne voit QUE ses propres actions
                    query = query.filter(JournalActivite.username == username_connecte)
            else:
                query = query.filter(JournalActivite.username == username_connecte)
        
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

            # --- 5. BOUTONS D'EXPORT CERTIFIÉ (CSV & PDF) ---
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
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                story = []
                styles = getSampleStyleSheet()
                
                title_style = ParagraphStyle(
                    'TitleStyle',
                    parent=styles['Heading1'],
                    fontSize=14,
                    textColor=colors.HexColor('#0d1b2a'),
                    spaceAfter=10
                )
                
                story.append(Paragraph(f"Piste d'Audit - {school_name}", title_style))
                story.append(Paragraph(f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
                story.append(Spacer(1, 15))
                
                table_data = [["Date", "Utilisateur", "Module", "Statut", "Action"]]
                for l in logs[:50]:
                    dt_s = l.timestamp.strftime("%d/%m/%Y %H:%M") if l.timestamp else ""
                    table_data.append([dt_s, str(l.username), str(l.module), str(l.statut), str(l.action)[:40]])
                
                t = Table(table_data, colWidths=[80, 70, 80, 60, 250])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d1b2a')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,0), 9),
                    ('BOTTOMPADDING', (0,0), (-1,0), 6),
                    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f9fa')),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
                    ('FONTSIZE', (0,1), (-1,-1), 8),
                ]))
                
                story.append(t)
                doc.build(story)
                pdf_data = pdf_buffer.getvalue()

                st.download_button(
                    label="📄 Exporter en PDF (Rapport)",
                    data=pdf_data,
                    file_name=f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
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